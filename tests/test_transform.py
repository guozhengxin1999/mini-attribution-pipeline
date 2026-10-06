import pytest
import pandas as pd
from etl.transform import transform

def test_dedup_keeps_last():
    rows = [
        {"date": "2026-10-06", 
         "campaign_id": "cmp_001", 
         "clicks": 100,
         "installs": 10, 
         "spend": 5.0, 
         "revenue": 12.0},
        {"date": "2026-10-06", 
         "campaign_id": "cmp_001", 
         "clicks": 200,
         "installs": 20, 
         "spend": 8.0, 
         "revenue": 20.0},
    ]

    df = transform(rows)
    assert len(df) == 1
    assert df.iloc[0]["clicks"] == 200   # keep="last"

def test_negative_spend_rejected():
    rows = [{"date": "2026-10-06", 
             "campaign_id": "cmp_001", 
             "clicks": 100,
             "installs": 10, 
             "spend": -1.0, 
             "revenue": 12.0}]
    with pytest.raises(ValueError, match="negative spend"):
        transform(rows)

def test_loaded_at_added():
    rows = [{"date": "2026-10-06", 
             "campaign_id": "cmp_001", 
             "clicks": 100,
             "installs": 10, 
             "spend": 5.0, 
             "revenue": 12.0}]
    df = transform(rows)
    assert "loaded_at" in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df["loaded_at"])
