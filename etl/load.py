import os
import json
import boto3
from dotenv import load_dotenv
from datetime import date
import psycopg2
from psycopg2.extras import execute_values


load_dotenv()

S3_BUCKET = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION")

DB_CONFIG = {
    "dbname": "attribution",
    "user": "postgres",
    "password": "pg",
    "host": "localhost",
    "port": "5432"
}

def upload_to_s3(partner: str, target_date: date, records: list[dict]):
    """
    Upload records to S3 using the path partition 
    `raw/partner=xxx/date=YYYY-MM-DD/data.json`. 
    Rerunning the process for the same day overwrites the same key, 
    ensuring idempotency.
    """
    if not S3_BUCKET:
        raise ValueError("S3_BUCKET_NAME is not set in .env")

    # Create an S3 client
    s3 = boto3.client("s3", region_name=AWS_REGION)

    # Construct partition path
    date_str = target_date.isoformat()
    key = f"raw/partner={partner}/date={date_str}/data.json"

    # Serialize data to JSON
    body = json.dumps(records)

    # Upload. `put_object` overwrites a Key with the same name, achieving idempotency.
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body)

    print(f"Uploaded {len(records)} records to s3://{S3_BUCKET}/{key}")
    return key

def load_to_postgres(partner: str, target_date: date, records: list[dict]):
    """
    Idempotent loading: Within a single transaction, 
    first delete the data for the specific partner for the current day, 
    then batch-insert the new data.
    """
    if not records:
        print("No records to load.")
        return

    conn = psycopg2.connect(**DB_CONFIG)
    
    insert_sql = """
        INSERT INTO fact_daily_performance 
        (date_id, partner_id, campaign_id, clicks, installs, spend, revenue)
        VALUES %s
    """
    
    # Convert a list of dictionaries into a list of tuples, with the order corresponding to the columns in SQL.
    values = [
        (r["date"], partner, r["campaign_id"], r["clicks"], r["installs"], r["spend"], r["revenue"])
        for r in records
    ]

    try:
        with conn:  # Start a transaction; it will automatically roll back if an error occurs.
            with conn.cursor() as cur:
                # 1. Delete the old data for that partner for the current day.
                cur.execute(
                    "DELETE FROM fact_daily_performance WHERE date_id = %s AND partner_id = %s",
                    (target_date, partner)
                )
                # 2. Bulk insert new data
                execute_values(cur, insert_sql, values)
        print(f"Successfully loaded {len(records)} records for {partner} on {target_date}.")
    except Exception as e:
        print(f"Failed to load data: {e}")
        raise
    finally:
        conn.close()