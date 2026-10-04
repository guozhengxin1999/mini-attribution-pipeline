# mini-attribution-pipeline
# Description: 
# This is a mini attribution pipeline project that simulates a partner API -> Python ETL -> S3 -> data warehouse -> SQL reporting workflow, orchestrated by Airflow, to demonstrate pagination/rate-limit handling, idempotent loading, reconciliation, data quality, and cloud cost awareness.

# What:
# Build an end-to-end attribution data pipeline that simulates daily campaign data from an MMP partner API, cleans it through ETL, lands it in S3, loads it into a data warehouse, and produces SQL reports and checks. Airflow orchestrates the whole flow, including backfills and duplicate-free reruns.


# Step 1: Mock API. Creates and activates a virtual environment named .venv
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn