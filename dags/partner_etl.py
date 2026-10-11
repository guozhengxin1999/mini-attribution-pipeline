import json
import os
from datetime import datetime, timedelta, date as date_type

import boto3
from airflow.sdk import dag, task, get_current_context

from etl.client import fetch_all
from etl.transform import transform
from etl.load import upload_to_s3, load_to_postgres

PARTNERS = ["partner_a", "partner_b"]
MOCK_API_BASE = "http://host.docker.internal:8000"

default_args = {
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
}


def get_ds() -> str:
    """Retrieve the logical date from the current task context in YYYY-MM-DD format."""
    ctx = get_current_context()
    dag_run = ctx["dag_run"]
    logical_date = dag_run.logical_date or dag_run.run_after
    return logical_date.strftime("%Y-%m-%d")

@dag(
    dag_id="partner_etl",
    schedule="0 2 * * *",
    start_date=datetime(2026, 9, 20),
    catchup=True,
    max_active_runs=1,
    default_args=default_args,
    tags=["attribution", "etl"],
)

def partner_etl():
    @task
    def extract_and_stage(partner: str) -> str:
        ds = get_ds()
        print(f"[extract] partner={partner} ds={ds}")

        rows = fetch_all(MOCK_API_BASE, ds)
        df = transform(rows)

        records = df.to_dict(orient="records")
        for r in records:
            r["date"] = r["date"].isoformat()
            r["loaded_at"] = r["loaded_at"].isoformat()

        s3_key = upload_to_s3(partner, date_type.fromisoformat(ds), records)
        return s3_key

    @task
    def load(s3_key: str) -> int:
        ds = get_ds()
        # key format：raw/partner=<partner>/date=<date>/data.json
        partner = s3_key.split("/")[1].split("=")[1]
        print(f"[load] partner={partner} ds={ds} s3_key={s3_key}")

        s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION"))
        obj = s3.get_object(Bucket=os.getenv("S3_BUCKET_NAME"), Key=s3_key)
        records = json.loads(obj["Body"].read())

        for r in records:
            r["date"] = date_type.fromisoformat(r["date"])

        load_to_postgres(partner, date_type.fromisoformat(ds), records)
        return len(records)
    
    @task
    def dq_check(counts: list[int]) -> None:
        ds = get_ds()
        total = sum(counts)
        print(f"[dq] ds={ds} total={total}")
        if total == 0:
            raise ValueError(f"DQ check failed for {ds}: no rows loaded")

    keys = extract_and_stage.expand(partner=PARTNERS)
    counts = load.expand(s3_key=keys)
    dq_check(counts)


partner_etl()