import json
import os
import io
import logging
from datetime import datetime
from decimal import Decimal
import boto3
import pandas as pd

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'clean_records')

def get_aqi_category(aqi):
    if aqi <= 50:
        return 'Good'
    elif aqi <= 100:
        return 'Moderate'
    elif aqi <= 150:
        return 'Unhealthy for Sensitive Groups'
    else:
        return 'Unhealthy/Hazardous'

def lambda_handler(event, context):
    logger.info(f"Received Event: {json.dumps(event)}")
    
    total_records = 0
    inserted_records = 0
    rejected_records = 0
    processed_files = []
    
    table = dynamodb.Table(TABLE_NAME)
   
    for record in event.get('Records', []):
        try:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            logger.info(f"Extracting Raw Data From S3 target: s3://{bucket}/{key}")
 
            file_extension = os.path.splitext(key)[1].lower()
            response = s3_client.get_object(Bucket=bucket, Key=key)
            raw_bytes = response['Body'].read()
            

            if file_extension == '.csv':
                df = pd.read_csv(io.StringIO(raw_bytes.decode('utf-8')))
                
            elif file_extension == '.json':
                try:
                    df = pd.read_json(io.StringIO(raw_bytes.decode('utf-8')))
                except ValueError:
                    df = pd.read_json(io.StringIO(raw_bytes.decode('utf-8')), lines=True)
                    
            elif file_extension == '.parquet':
                df = pd.read_parquet(io.BytesIO(raw_bytes))
                
            elif file_extension == '.txt':
                df = pd.read_csv(io.StringIO(raw_bytes.decode('utf-8')), sep=None, engine='python')
                
            else:
                logger.error(f"Unsupported file format extension detected: {file_extension} for file s3://{bucket}/{key}")
                continue
                
        except Exception as e:
            logger.error(f"Extraction Phase Aborted for single record file: {str(e)}")
            continue

        total_records += len(df)
        processed_files.append({"file": f"s3://{bucket}/{key}", "type": file_extension})
        
        for index, row in df.iterrows():
            try:
                if pd.isna(row['city']) or str(row['city']).strip().lower() == 'unknown' or pd.isna(row['aqi']) or float(row['aqi']) < 0:
                    logger.warning(f"Row [{index}] Skipped in file {key}: Missing metrics.")
                    rejected_records += 1
                    continue
                
                clean_city = str(row['city']).strip().upper()
                clean_country = str(row['country']).strip().upper() if not pd.isna(row['country']) else "UNKNOWN"
                
                raw_ts = str(row['raw_timestamp']).strip()
                
                try:
                    clean_timestamp = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S").isoformat()
                except ValueError:
                    clean_timestamp = pd.to_datetime(raw_ts).isoformat()
                
                aqi_val = int(row['aqi'])
                aqi_cat = get_aqi_category(aqi_val)
                
                record_id = f"{clean_city}#{clean_timestamp}"
                pm25_val = Decimal(str(row['pm25'])) if not pd.isna(row['pm25']) else Decimal('0.0')
                
                item = {
                    'record_id': record_id,
                    'city': clean_city,
                    'country': clean_country,
                    'aqi': aqi_val,
                    'pm25': pm25_val,
                    'timestamp': clean_timestamp,
                    'aqi_category': aqi_cat,
                    'processed_at': datetime.utcnow().isoformat()
                }
                
                table.put_item(Item=item)
                inserted_records += 1
                
            except Exception as item_error:
                logger.error(f"Failed processing row index [{index}] in file {key}: {str(item_error)}")
                rejected_records += 1

    audit_log = {
        "execution_timestamp": datetime.utcnow().isoformat(),
        "processed_files_summary": processed_files,
        "total_input_records_all_files": total_records,
        "successfully_inserted": inserted_records,
        "rejected_records": rejected_records
    }
    
    logger.info(f"BATCED AUDIT SUMMARY: {json.dumps(audit_log)}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(audit_log)
    }