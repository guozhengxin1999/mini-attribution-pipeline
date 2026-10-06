import pandas as pd

REQUIRED = ["date", "campaign_id", "clicks", "installs", "spend", "revenue"]

def transform(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)

    # 1. Field rename
    df = df.rename(columns={"campaign_id": "campaign_id"})

    # 2. Type conversion
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["campaign_id"] = df["campaign_id"].astype(str)
    for col in ["clicks", "installs"]:
        df[col] = df[col].astype("int64")
    for col in ["spend", "revenue"]:
        df[col] = df[col].astype("float64")

    # 3. Deduplication: (data, campaign_id) is unique.
    df = df.drop_duplicates(subset=["date", "campaign_id"], keep="last")

    # 4. Dirty data check
    if (df["spend"] < 0).any():
        raise ValueError("negative spend found")
    if (df["revenue"] < 0).any():
        raise ValueError("negative revenue found")
    if df["campaign_id"].isna().any():
        raise ValueError("null campaign_id found")

     # 5. loaded_at
    df["loaded_at"] = pd.Timestamp.utcnow()

    # 6. List order
    return df[REQUIRED + ["loaded_at"]]

 