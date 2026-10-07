CREATE DATABASE attribution;
\c attribution;

CREATE TABLE fact_daily_performance (
    date_id DATE NOT NULL,
    partner_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    clicks INTEGER,
    installs INTEGER,
    spend NUMERIC(12, 2),
    revenue NUMERIC(12, 2),
    loaded_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date_id, partner_id, campaign_id)
);