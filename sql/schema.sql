DROP TABLE IF EXISTS fact_daily_performance CASCADE;

CREATE TABLE fact_daily_performance (
    date_id      DATE          NOT NULL,
    partner_id   TEXT          NOT NULL,
    campaign_id  TEXT          NOT NULL,
    clicks       INTEGER,
    installs     INTEGER,
    spend        NUMERIC(12, 2),
    revenue      NUMERIC(12, 2),
    loaded_at    TIMESTAMPTZ   DEFAULT NOW(),
    PRIMARY KEY (date_id, partner_id, campaign_id)
);

-- Dimension Table: Partner
DROP TABLE IF EXISTS dim_partner CASCADE;

CREATE TABLE dim_partner (
    partner_id TEXT PRIMARY KEY,
    partner_name TEXT NOT NULL
);


-- Dimension Table: Activity
DROP TABLE IF EXISTS dim_campaign CASCADE;

CREATE TABLE dim_campaign (
    campaign_id TEXT PRIMARY KEY,
    campaign_name TEXT NOT NULL,
    partner_id TEXT REFERENCES dim_partner(partner_id)
);

-- Dimension Table: Date
DROP TABLE IF EXISTS dim_date CASCADE;

CREATE TABLE dim_date (
    date_id DATE PRIMARY KEY,
    year INT,
    month INT,
    day INT,
    weekday INT
);


INSERT INTO dim_partner (partner_id, partner_name) VALUES
    ('partner_a', 'Partner A'),
    ('partner_b', 'Partner B')
ON CONFLICT (partner_id) DO NOTHING;

INSERT INTO dim_campaign (campaign_id, campaign_name, partner_id) VALUES
    ('cmp_001', 'Campaign 001', 'partner_a'),
    ('cmp_002', 'Campaign 002', 'partner_a'),
    ('cmp_003', 'Campaign 003', 'partner_b')
ON CONFLICT (campaign_id) DO NOTHING;

INSERT INTO dim_date (date_id, year, month, day, weekday)
SELECT
    d::date,
    EXTRACT(YEAR FROM d),
    EXTRACT(MONTH FROM d),
    EXTRACT(DAY FROM d),
    EXTRACT(DOW FROM d)
FROM generate_series('2026-10-01'::date, '2026-10-31'::date, '1 day') AS d
ON CONFLICT (date_id) DO NOTHING;