import json
import os
import io
import logging
from datetime import datetime
import boto3
import pandas as pd

# Setup Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Env variable fallback for flexibility
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'clean_records')

def get_aqi_category(aqi):
    """Derived Field Logic: Categorizes AQI value"""
    if aqi <= 50:
        return 'Good'
    elif aqi <= 100:
        return 'Moderate'
    elif aqi <= 150:
        return 'Unhealthy for Sensitive Groups'
    else:
        return 'Unhealthy/Hazardous'

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    # 1. EXTRACT: Parse S3 bucket and key from the trigger event
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        logger.info(f"Extracting raw data from S3: s3://{bucket}/{key}")
        
        response = s3_client.get_object(Bucket=bucket, Key=key)
        raw_data = response['Body'].read().decode('utf-8')
        df = pd.read_csv(io.StringIO(raw_data))
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        raise e

    total_records = len(df)
    inserted_records = 0
    rejected_records = 0
    
    table = dynamodb.Table(TABLE_NAME)
    
    # 2. TRANSFORM & LOAD
    for index, row in df.iterrows():
        try:
            # Rule 1: Remove/Skip invalid records (Missing city or invalid AQI)
            if pd.isna(row['city']) or row['city'] == 'Unknown' or pd.isna(row['aqi']) or float(row['aqi']) < 0:
                logger.warning(f"Row {index} rejected: Invalid AQI or missing City metrics.")
                rejected_records += 1
                continue
            
            # Rule 2: Standardize Fields
            clean_city = str(row['city']).strip().upper()
            clean_country = str(row['country']).strip().upper()
            
            # Standardize date formats to clean ISO strings
            raw_ts = str(row['raw_timestamp'])
            clean_timestamp = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S").isoformat()
            
            # Rule 3: Create Derived Field
            aqi_val = int(row['aqi'])
            aqi_cat = get_aqi_category(aqi_val)
            
            # Generate Unique Partition Key
            record_id = f"{clean_city}#{clean_timestamp}"
            
            item = {
                'record_id': record_id,
                'city': clean_city,
                'country': clean_country,
                'aqi': aqi_val,
                'pm25': float(row['pm25']) if not pd.isna(row['pm25']) else 0.0,
                'timestamp': clean_timestamp,
                'aqi_category': aqi_cat,
                'processed_at': datetime.utcnow().isoformat()
            }
            
            # 3. LOAD: Write to DynamoDB
            table.put_item(Item=item)
            inserted_records += 1
            
        except Exception as item_error:
            logger.error(f"Failed processing row {index}: {str(item_error)}")
            rejected_records += 1

    # 4. AUDIT SUMMARY
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