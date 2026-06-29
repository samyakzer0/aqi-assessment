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
    
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        logger.info(f"Extracting Raw Data From S3 target: s3://{bucket}/{key}")
        
        response = s3_client.get_object(Bucket=bucket, Key=key)
        raw_data = response['Body'].read().decode('utf-8')
        df = pd.read_csv(io.StringIO(raw_data))
    except Exception as e:
        logger.error(f"Extraction Phase Aborted: {str(e)}")
        raise e

    total_records = len(df)
    inserted_records = 0
    rejected_records = 0
    
    table = dynamodb.Table(TABLE_NAME)
    
    for index, row in df.iterrows():
        try:
            if pd.isna(row['city']) or str(row['city']).strip().lower() == 'unknown' or pd.isna(row['aqi']) or float(row['aqi']) < 0:
                logger.warning(f"Row [{index}] Skipped: Missing metrics.")
                rejected_records += 1
                continue
            
            clean_city = str(row['city']).strip().upper()
            clean_country = str(row['country']).strip().upper() if not pd.isna(row['country']) else "UNKNOWN"
            
            raw_ts = str(row['raw_timestamp']).strip()
            clean_timestamp = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S").isoformat()
            
            aqi_val = int(row['aqi'])
            aqi_cat = get_aqi_category(aqi_val)
            
            record_id = f"{clean_city}#{clean_timestamp}"
            
            # Using Decimal(str(...)) prevents floating point precision errors in DynamoDB
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
            logger.error(f"Failed processing row index [{index}]: {str(item_error)}")
            rejected_records += 1

    audit_log = {
        "execution_timestamp": datetime.utcnow().isoformat(),
        "input_file": f"s3://{bucket}/{key}",
        "total_input_records": total_records,
        "successfully_inserted": inserted_records,
        "rejected_records": rejected_records
    }
    
    logger.info(f"AUDIT SUMMARY: {json.dumps(audit_log)}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(audit_log)
    }