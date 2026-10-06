import pytest
import responses
from etl.client import fetch_all

BASE = "http://testserver"

def make_rows(start, n):
    return [
        {
            "date": "2026-10-06",
            "campaign_id": f"cmp_{i:03d}", 
            "clicks": 100,
            "installs": 10, 
            "spend": 5.0, 
            "revenue": 12.0
        }
        for i in range(start, start + n)
    ]

@responses.activate
def test_multi_page_concat():
    responses.add(responses.GET, f"{BASE}/v1/reports",
                  json={"data": make_rows(1, 20), "next_cursor": 20}, 
                  status=200)
    responses.add(responses.GET, f"{BASE}/v1/reports",
                  json={"data": make_rows(21, 20), "next_cursor": 40}, 
                  status=200)
    responses.add(responses.GET, f"{BASE}/v1/reports",
                  json={"data": make_rows(41, 5), "next_cursor": None}, 
                  status=200)

    rows = fetch_all(BASE, "2026-10-06")
    assert len(rows) == 45
    assert rows[0]["campaign_id"] == "cmp_001"
    assert rows[-1]["campaign_id"] == "cmp_045"

@responses.activate
def test_429_retry_respects_retry_after(monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", lambda s: slept.append(s))
    responses.add(responses.GET, 
                  f"{BASE}/v1/reports",
                  status=429,
                  headers={"Retry-After": "1"})
    responses.add(responses.GET, 
                  f"{BASE}/v1/reports",
                  json={"data": make_rows(1, 20), "next_cursor": None}, 
                  status=200)
    rows = fetch_all(BASE, "2026-10-06")
    assert len(rows) == 20
    assert slept == [1.0]

@responses.activate
def test_500_then_give_up(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)

    for _ in range(5):
        responses.add(responses.GET, 
                      f"{BASE}/v1/reports", 
                      status=500)

    with pytest.raises(RuntimeError, match="gave up"):
        fetch_all(BASE, "2026-10-06", max_retries=5)

@responses.activate
def test_empty_page():
    responses.add(responses.GET, 
                  f"{BASE}/v1/reports",
                  json={"data": [], "next_cursor": None}, 
                  status=200)

    rows = fetch_all(BASE, "2026-10-06")
    assert rows == []