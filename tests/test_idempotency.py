from etl.load import load_to_postgres, DB_CONFIG
from datetime import date
import psycopg2

# Simulate three identical records.
mock_records = [
    {"date": date(2026, 10, 4), "campaign_id": "cmp_001", "clicks": 100, "installs": 10, "spend": 5.0, "revenue": 12.0},
    {"date": date(2026, 10, 4), "campaign_id": "cmp_002", "clicks": 200, "installs": 20, "spend": 10.0, "revenue": 24.0},
]

# Clear the table for a clean test.
conn = psycopg2.connect(**DB_CONFIG)
with conn:
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE fact_daily_performance;")
conn.close()

# Run three times
for i in range(3):
    print(f"\n--- Run {i+1} ---")
    load_to_postgres("partner_a", date(2026, 10, 4), mock_records)

# Verification results
conn = psycopg2.connect(**DB_CONFIG)
with conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), SUM(spend), SUM(revenue) FROM fact_daily_performance")
        count, total_spend, total_revenue = cur.fetchone()
        print(f"\nFinal state: {count} rows, total spend = {total_spend}, total revenue = {total_revenue}")
        assert count == 2, "Idempotency failed: expected 2 rows"
conn.close()