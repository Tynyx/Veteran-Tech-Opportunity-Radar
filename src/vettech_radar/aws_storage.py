import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import boto3

def get_dynmaodb_table():
    """Return the DynamoDB table resource."""
    table_name = os.getenv("DYNAMODB_TABLE_NAME")

    if not table_name: 
        raise ValueError("Misssing DYNAMODB_TABLE_NAME environment variable.")
    
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)

def get_s3_client():
    """Return the s3 cleint."""
    bucket_name = os.getenv("S3_BUCKET_NAME")


    if not bucket_name:
        raise ValueError("Missing S3_BUCKET_NAME environment variable.")
    
    return boto3.client("s3")

def convert_floats_to_decimal(value):
    """
    Convert floats to Decimal because DynamoDB does not store python float values directly.
    """
    
    if isinstance(value, float):
        return Decimal(str(value))
    
    if isinstance(value, dict):
        return {
            key: convert_floats_to_decimal(nested_value)
            for key, nested_value in value.items()

        }
    
    if isinstance(value, list):
        return [convert_floats_to_decimal(item) for item in value]
    
    return value

def create_record_id(clean_record):
    """ Create a unique reocrd |ID for DynamoDB."""
    collected_date = str(clean_record.get('date_collected', ""))[:10]
    search_term = str(clean_record.get("search_term", "unknown")).replace(" ", "_").lower()
    job_id = str(clean_record.get("job_id", "unknown")).replace(" ", "_").lower()

    return f"{collected_date}#{search_term}#{job_id}"

def save_clean_records_to_dynamodb(clean_records):
    """Save the clean job records to DynamoDB."""
    table = get_dynmaodb_table()
    saved_count = 0

    for record in clean_records:
        record["record_id"] = create_record_id(record)
        safe_record = convert_floats_to_decimal(record)
        table.put_item(Item=safe_record)
        saved_count += 1

    return saved_count

def save_raw_json_to_s3(data, search_term, timestamp):
    """Save raw API JSON response to s3.""" 
    bucket_name = os.getenv("S3_BUCKET_NAME")

    if not bucket_name:
        raise ValueError("Missing S3_BUCKET_NAME environment variable.")
    
    safe_search = search_term.replace(" ", "_").replace("/", "_").lower()

    today = datetime.now()
    key = (
        f"raw_data/{today.year}/{today.month:02d}/{today.day:02d}/"
        f"{safe_search}_{timestamp}.json"
    )

    s3 = get_s3_client()

    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(data, ihdent=2),
        ContentType="application/json",
    )

    return f"s3://{bucket_name}/{key}"