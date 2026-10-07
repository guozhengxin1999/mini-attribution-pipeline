-- 7-day rolling ROAS (Return on Ad Spend)
SELECT
    date_id,
    campaign_id,
    SUM(revenue) OVER (PARTITION BY campaign_id ORDER BY date_id ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) 
    / 
    NULLIF(SUM(spend) OVER (PARTITION BY campaign_id ORDER BY date_id ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 0) 
    AS roas_7d
FROM fact_daily_performance
ORDER BY campaign_id, date_id;


-- For each partner, select the top 5 campaigns ranked by spend.
WITH ranked_campaigns AS (
    SELECT
        partner_id,
        campaign_id,
        SUM(spend) AS total_spend,
        RANK() OVER (PARTITION BY partner_id ORDER BY SUM(spend) DESC) AS rk
    FROM fact_daily_performance
    GROUP BY partner_id, campaign_id
)
SELECT *
FROM ranked_campaigns
WHERE rk <= 5
ORDER BY partner_id, rk;

-- Day-over-day change: Today's spend vs. yesterday's spend
SELECT
    date_id,
    SUM(spend) AS daily_spend,
    LAG(SUM(spend), 1) OVER (ORDER BY date_id) AS prev_day_spend,
    (SUM(spend) - LAG(SUM(spend), 1) OVER (ORDER BY date_id)) 
    / NULLIF(LAG(SUM(spend), 1) OVER (ORDER BY date_id), 0) * 100 AS pct_change
FROM fact_daily_performance
GROUP BY date_id
ORDER BY date_id;


-- Reconciliation: Compare the aggregated values ​​returned by the API with the aggregated values ​​from the warehouse.
WITH api_summary AS (
    SELECT '2026-10-07'::date AS date_id, 300 AS expected_clicks, 30 AS expected_installs
),
warehouse_summary AS (
    SELECT 
        date_id, 
        SUM(clicks) AS actual_clicks, 
        SUM(installs) AS actual_installs
    FROM fact_daily_performance
    WHERE date_id = '2026-10-07'
    GROUP BY date_id
)
SELECT
    a.date_id,
    a.expected_clicks,
    w.actual_clicks,
    a.expected_installs,
    w.actual_installs,
    CASE WHEN a.expected_clicks != w.actual_clicks OR a.expected_installs != w.actual_installs THEN 'MISMATCH' ELSE 'OK' END AS status
FROM api_summary a
JOIN warehouse_summary w ON a.date_id = w.date_id;