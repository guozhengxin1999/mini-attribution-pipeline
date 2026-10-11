# Mini Attribution Pipeline

An end-to-end data pipeline that simulates ingesting daily marketing attribution data from a partner API, transforms it, stages it in S3, loads it into PostgreSQL, and produces analytical SQL — orchestrated by Airflow.

Runs entirely locally with Docker and AWS Free Tier at zero cost.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Running the Pipeline](#running-the-pipeline)
- [Design Decisions](#design-decisions)
- [Idempotency](#idempotency)
- [Testing](#testing)
- [Key Problems Solved](#key-problems-solved)
- [Future Improvements](#future-improvements)

---

## Overview

```
Partner API → Python ETL → S3 → Warehouse → SQL Reports
                    ↑
              Airflow DAG
```

**Capabilities demonstrated:**

- Fault-tolerant API ingestion — pagination, rate-limit handling, exponential backoff
- Three-layer idempotency — API, S3, and warehouse
- Dimensional modeling — star schema with fact and dimension tables
- Analytical SQL — rolling windows, ranking, reconciliation
- Airflow orchestration — daily scheduling, dynamic task mapping, backfill

---

## Tech Stack

| Layer | Technology |
|---|---|
| API mock | FastAPI, Uvicorn |
| ETL | Python 3.13, requests, pandas |
| Storage | AWS S3 (boto3) |
| Warehouse | PostgreSQL 16 (Docker) |
| Orchestration | Apache Airflow 3.x (Docker Compose) |
| Testing | pytest, responses |

---

## Getting Started

### Prerequisites

- Docker Desktop (≥ 4 GB memory)
- Python 3.11+
- AWS account with an S3 bucket and a scoped IAM user

### 1. Set up AWS

1. Create an S3 bucket. Leave **Block Public Access** enabled.
2. Create an IAM user with a least-privilege policy:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": [
         "s3:PutObject",
         "s3:GetObject",
         "s3:ListBucket",
         "s3:GetBucketLocation"
       ],
       "Resource": [
         "arn:aws:s3:::YOUR-BUCKET",
         "arn:aws:s3:::YOUR-BUCKET/*"
       ]
     }]
   }
   ```

3. Generate an access key. Save it in `.env`:

   ```env
   AWS_ACCESS_KEY_ID=...
   AWS_SECRET_ACCESS_KEY=...
   AWS_DEFAULT_REGION=eu-north-1
   S3_BUCKET_NAME=your-bucket-name
   POSTGRES_HOST=host.docker.internal
   AIRFLOW_UID=501
   FERNET_KEY=...
   _PIP_ADDITIONAL_REQUIREMENTS=requests pandas boto3 python-dotenv psycopg2-binary
   ```

4. Add `.env` to `.gitignore`.

### 2. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Start PostgreSQL

```bash
docker run --name pg-attribution -p 5432:5432 \
  -e POSTGRES_PASSWORD=pg \
  -v pgdata:/var/lib/postgresql/data \
  -d postgres:16

docker exec -i pg-attribution psql -U postgres -c "CREATE DATABASE attribution;"
docker exec -i pg-attribution psql -U postgres -d attribution < sql/schema.sql
```

### 4. Start Airflow

```bash
docker compose up airflow-init
docker compose up -d
```

- UI: <http://localhost:8080>
- Credentials: `airflow` / `airflow`

---

## Running the Pipeline

### 1. Start the mock API

```bash
uvicorn mock_api.main:app --host 0.0.0.0 --port 8000
```

> The `--host 0.0.0.0` flag is required so Airflow containers can reach the API via `host.docker.internal`.

### 2. Trigger a single run

```bash
docker compose exec airflow-scheduler \
  airflow dags trigger partner_etl --logical-date "2026-10-07"
```

### 3. Backfill a date range

```bash
docker compose exec airflow-scheduler airflow backfill create \
  --dag-id partner_etl \
  --from-date 2026-09-20 \
  --to-date 2026-10-08
```

> In Airflow 3.x, the end date is **exclusive**. To include `2026-10-07`, use `--to-date 2026-10-08`.

### 4. Verify idempotency

```bash
# Capture baseline
docker exec -i pg-attribution psql -U postgres -d attribution <<'SQL' | tee /tmp/baseline.txt
SELECT date_id, COUNT(*), SUM(spend), SUM(revenue)
FROM fact_daily_performance
WHERE date_id BETWEEN '2026-09-20' AND '2026-10-07'
GROUP BY date_id ORDER BY date_id;
SQL

# Rerun the backfill
docker compose exec airflow-scheduler airflow backfill create \
  --dag-id partner_etl --from-date 2026-09-20 --to-date 2026-10-08

# Capture again
docker exec -i pg-attribution psql -U postgres -d attribution <<'SQL' | tee /tmp/after.txt
SELECT date_id, COUNT(*), SUM(spend), SUM(revenue)
FROM fact_daily_performance
WHERE date_id BETWEEN '2026-09-20' AND '2026-10-07'
GROUP BY date_id ORDER BY date_id;
SQL

# Diff
diff /tmp/baseline.txt /tmp/after.txt && echo "Idempotency verified"
```

---

## Design Decisions

### Star schema

Fact table stores measures; dimension tables store descriptive attributes. Smaller fact table means faster aggregation; adding a new dimension only touches the fact table's foreign keys.

### Composite primary key `(date_id, partner_id, campaign_id)`

Reflects the business uniqueness rule — one row per campaign per partner per day. It also serves as the conflict target for `ON CONFLICT DO UPDATE`, which is what makes idempotency enforceable at the database level.

### UPSERT instead of DELETE + INSERT

DELETE + INSERT breaks under concurrent backfills — two runs can each delete-then-insert the same partition and collide. UPSERT resolves the conflict in the database and is faster when most rows are unchanged.

### `NUMERIC(12,2)` for money

Floating point introduces rounding errors that accumulate across rows and break reconciliation. Exact decimal is required for currency.

### `TEXT` for IDs

The source emits strings (`"partner_a"`, `"cmp_001"`). Integer surrogate keys would add a mapping table without benefit at this scale.

### `logical_date or run_after` fallback

In Airflow 3.x, `ds` is not auto-injected into dynamically-mapped tasks, and manually-triggered runs have `logical_date = None`. Falling back to `run_after` makes the DAG work under cron, backfill, and manual trigger without change.

---

## Idempotency

Three independent layers, so no single point of failure can break it.

| Layer | Mechanism |
|---|---|
| API | `random.Random(date)` — same date always returns the same data |
| S3 | Overwrite same key `raw/partner=xxx/date=yyyy-mm-dd/data.json` |
| Warehouse | `ON CONFLICT (date_id, partner_id, campaign_id) DO UPDATE` |

Verified end to end: a full 18-day backfill was run twice and the aggregate results were diffed — output is identical.

---

## Testing

```bash
pytest -v
```

**Client tests**

- Multi-page concatenation (3 pages → 45 rows)
- 429 retry respects `Retry-After`
- Consecutive 500s raise `RuntimeError`
- Empty page returns `[]`

**Transform tests**

- Dedup keeps last record
- Negative spend rejected
- `loaded_at` populated

HTTP is mocked with `responses`; `time.sleep` is patched with `monkeypatch` so retries do not actually wait.

---

## Key Problems Solved

| Problem | Root Cause | Solution |
|---|---|---|
| Airflow worker kept restarting | `DB_HOST` is reserved by Airflow (used for Redis) | Renamed to `POSTGRES_HOST` |
| `KeyError: 'ds'` in mapped tasks | `ds` not auto-injected in Airflow 3.x dynamic mapping | Read `dag_run.logical_date` instead |
| `AttributeError: 'NoneType'...strftime` | Manual trigger sets `logical_date = None` | Fallback to `run_after` |
| `TypeError: missing argument 'partner'` | Signature and `.expand()` args mismatched | Parsed partner from S3 key |
| `dq_check total=180` (expected 90) | `.expand()` on two lists → Cartesian product | Expanded a single argument |
| `airflow dags backfill` not found | Command moved in Airflow 3.x | Used `airflow backfill create` |
| `InvalidRegionError` | Region was console label, not code | Used `eu-north-1` |
| Duplicate key on concurrent backfill | DELETE + INSERT not concurrency-safe | Switched to UPSERT |

---

## Future Improvements

- Parquet in S3 for columnar reads
- dbt for transformations and lineage
- Great Expectations for declarative data quality
- Slack alerts on `dq_check` failure
- Redshift migration — replace `INSERT` with `COPY`, add `DISTKEY` / `SORTKEY`