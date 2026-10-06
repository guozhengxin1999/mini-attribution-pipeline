# etl/client.py
import time, requests

def fetch_all(base_url, date, session=None, max_retries=5):
    s = session or requests.Session()
    cursor, rows = 0, []
    while cursor is not None:
        for attempt in range(max_retries):
            r = s.get(f"{base_url}/v1/reports",
                      params={"date": date, "cursor": cursor}, timeout=10)
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 2 ** attempt)))
            elif r.status_code >= 500:
                time.sleep(2 ** attempt)
            else:
                r.raise_for_status()
                break
        else:
            raise RuntimeError(f"gave up on {date} cursor={cursor}")
        body = r.json()
        rows += body["data"]
        cursor = body["next_cursor"]
    return rows