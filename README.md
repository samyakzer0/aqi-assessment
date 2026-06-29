# AQI Serverless ETL Pipeline
[](https://github.com/samyakzer0/aqi-assessment#earthquake-serverless-etl-pipeline)

## Project Overview
[](https://github.com/samyakzer0/aqi-assessment#project-overview)
This project implements a serverless ETL pipeline using Amazon S3, AWS Lambda, Amazon DynamoDB, Amazon CloudWatch, GitHub Actions, AWS CodeBuild, and AWS CodePipeline.

The pipeline processes air quality data stored in a CSV file. Invalid records are rejected, valid records are cleaned and transformed, and the final records are stored in DynamoDB.

## Dataset Source
[](https://github.com/samyakzer0/aqi-assessment#dataset-source)
This project uses a sample AQI CSV dataset created for this assignment and inspired by common air quality monitoring records.

The dataset contains the following fields:

- City
- AQI
- PM2.5
- Raw timestamp
- Country

## ETL Scenario
[](https://github.com/samyakzer0/aqi-assessment#etl-scenario)
The purpose of this project is to prepare clean air quality records for analytics, monitoring, or alerting.

The raw AQI CSV file is uploaded to the `raw/` prefix in Amazon S3. The upload triggers an AWS Lambda function.

The Lambda function reads the file, validates the records, transforms the valid records, and stores the clean data in Amazon DynamoDB.

## Architecture
[](https://github.com/samyakzer0/aqi-assessment#architecture)

```
AQI CSV Data
	|
	v
Amazon S3 raw/
	|
	v
AWS Lambda ETL Function
	|
	v
Amazon DynamoDB clean_records
	|
	v
Amazon CloudWatch Logs

GitHub Repository
	|
	v
GitHub Actions
	|
	v
AWS CodePipeline
	|
	v
AWS CodeBuild
	|
	v
AWS Lambda Deployment
```

## AWS Services Used
[](https://github.com/samyakzer0/aqi-assessment#aws-services-used)

- Amazon S3
- AWS Lambda
- Amazon DynamoDB
- Amazon CloudWatch
- AWS Identity and Access Management
- AWS CodeBuild
- AWS CodePipeline

## ETL Process
[](https://github.com/samyakzer0/aqi-assessment#etl-process)

### Extract
[](https://github.com/samyakzer0/aqi-assessment#extract)
The Lambda function reads the CSV file from:

```
s3://<your-bucket-name>/raw/sample_raw_data.csv
```

### Transform
[](https://github.com/samyakzer0/aqi-assessment#transform)
The Lambda function applies the following transformation rules:

1. Removes records with a missing city.
2. Removes records with the literal value `unknown` in the city field.
3. Removes records with a missing AQI value.
4. Removes records with a negative AQI value.
5. Standardizes the city field using uppercase.
6. Standardizes the country field using uppercase.
7. Converts AQI and PM2.5 into numeric values.
8. Converts the raw timestamp into ISO 8601 format.
9. Adds a derived `aqi_category` field.
10. Adds a `processed_at` timestamp.

### AQI Category Rules
[](https://github.com/samyakzer0/aqi-assessment#severity-rules)

- AQI less than or equal to `50` → `Good`
- AQI less than or equal to `100` → `Moderate`
- AQI less than or equal to `150` → `Unhealthy for Sensitive Groups`
- AQI greater than `150` → `Unhealthy/Hazardous`

### Load
[](https://github.com/samyakzer0/aqi-assessment#load)
The clean records are written to the DynamoDB table:

```
clean_records
```

## DynamoDB Table Design
[](https://github.com/samyakzer0/aqi-assessment#dynamodb-table-design)

- Table name: `clean_records`
- Partition key: `record_id`
- Partition key type: `String`
- Capacity mode: `On-demand`
The `record_id` field uniquely identifies each air quality record.

## Audit Logging
[](https://github.com/samyakzer0/aqi-assessment#audit-logging)
The Lambda function writes an audit summary to Amazon CloudWatch Logs.

The audit summary includes:

- Total input records
- Successfully inserted records
- Rejected records
- Execution timestamp

### Test Result
[](https://github.com/samyakzer0/aqi-assessment#test-result)

```
Total input records: 5
Successfully inserted records: 5
Rejected records: 0
```

The following records were inserted:

```
INDORE#2026-06-29T10:00:00
MUMBAI#2026-06-29T10:05:00
DELHI#2026-06-29T10:10:00
NEW YORK#2026-06-29T10:15:00
LONDON#2026-06-29T10:20:00
```

## S3 Trigger
[](https://github.com/samyakzer0/aqi-assessment#s3-trigger)
An S3 trigger is connected to the Lambda function.

Trigger settings:

- Bucket: `<your-bucket-name>`
- Prefix: `raw/`
- Suffix: `.csv`
- Event type: `All object create events`
Whenever a CSV file is uploaded to the `raw/` prefix, the Lambda function runs automatically.

## Testing Steps
[](https://github.com/samyakzer0/aqi-assessment#testing-steps)

1. Upload `sample_raw_data.csv` to the S3 `raw/` prefix.
2. Confirm that S3 triggers the Lambda function.
3. Check the Lambda execution result.
4. Open CloudWatch Logs and verify the audit summary.
5. Open DynamoDB and scan the `clean_records` table.
6. Confirm that the clean records were inserted.

## GitHub Actions
[](https://github.com/samyakzer0/aqi-assessment#github-actions)
The GitHub Actions workflow runs on every push and pull request.

It performs the following steps:

1. Checks out the repository.
2. Sets up Python 3.11.
3. Installs dependencies from `requirements.txt`.
4. Validates the Lambda syntax using:

```
python -m py_compile lambda_function.py
```

## AWS CodePipeline
[](https://github.com/samyakzer0/aqi-assessment#aws-codepipeline)
The AWS CodePipeline contains the following stages:

```
Source → Build → Deploy
```

### Source Stage
[](https://github.com/samyakzer0/aqi-assessment#source-stage)
The Source stage reads the project from:

```
https://github.com/samyakzer0/aqi-assessment
```

Branch:

```
main
```

### Build Stage
[](https://github.com/samyakzer0/aqi-assessment#build-stage)
AWS CodeBuild uses `buildspec.yml` to:

- Install dependencies
- Validate the Lambda syntax
- Create the build artifact

### Deploy Stage
[](https://github.com/samyakzer0/aqi-assessment#deploy-stage)
The Deploy stage updates the existing Lambda function:

```
earthquake-etl-function
```

## Repository Structure
[](https://github.com/samyakzer0/aqi-assessment#repository-structure)

```
aqi/
│
├── sample_data/
│   └── sample_raw_data.csv
│
├── screenshots/
├── buildspec.yml
├── lambda_function.py
├── README.md
└── requirements.txt
```

## Security
[](https://github.com/samyakzer0/aqi-assessment#security)
The project does not store:

- AWS access keys
- AWS secret keys
- Credentials
- `.env` files
- ZIP packages
- Generated dependency folders

The S3 bucket blocks public access.

For this beginner project, the following AWS-managed policies were used:

```
AmazonS3ReadOnlyAccess
AmazonDynamoDBFullAccess
AWSLambdaBasicExecutionRole
```

In a production project, these should be replaced with a least-privilege custom IAM policy.

## Final Result
[](https://github.com/samyakzer0/aqi-assessment#final-result)
This project successfully demonstrates:

- Raw air quality data stored in Amazon S3
- Automatic processing using AWS Lambda
- Invalid record removal
- Field standardization
- Derived AQI category creation
- Clean records stored in DynamoDB
- Audit logs stored in CloudWatch
- GitHub version control
- Successful GitHub Actions validation
- Successful AWS CodeBuild execution
- Successful AWS CodePipeline deployment
