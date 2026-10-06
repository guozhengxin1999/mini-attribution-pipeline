# mock_api/main.py
import random
from fastapi import FastAPI, HTTPException

app = FastAPI()
CAMPAIGNS = [f"cmp_{i:03d}" for i in range(1, 46)]
PAGE_SIZE = 20
calls = 0

@app.get("/v1/reports")
def reports(date: str, cursor: int = 0):
    global calls
    calls += 1
    if calls % 7 == 0:
        raise HTTPException(429, headers={"Retry-After": "1"})
    if calls % 11 == 0:
        raise HTTPException(500, "upstream error")

    rng = random.Random(date)         
    rows = []
    for c in CAMPAIGNS:
        clicks = rng.randint(500, 5000)
        installs = int(clicks * rng.uniform(0.02, 0.1))
        rows.append({
            "date": date, "campaign_id": c, "clicks": clicks,
            "installs": installs,
            "spend": round(installs * rng.uniform(0.5, 2.5), 2),
            "revenue": round(installs * rng.uniform(0.3, 3.0), 2),
        })
    nxt = cursor + PAGE_SIZE
    return {"data": rows[cursor:nxt], "next_cursor": nxt if nxt < len(rows) else None}