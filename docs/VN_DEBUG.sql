-- VN DATA DEBUG QUERIES
-- Purpose: Check if VN has any data and identify filter issues

-- Query 1: Check if VN has ANY data in silver table
SELECT
    COUNT(*) AS total_records,
    COUNT(DISTINCT orderNumber) AS unique_orders,
    COUNT(DISTINCT beesAccountId) AS unique_buyers,
    MIN(createAt) AS earliest_order,
    MAX(createAt) AS latest_order
FROM ptn_am.silver.vn_daily_orders_consolidated
WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 7 HOUR)) >= '2026-01-01'
AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 7 HOUR)) <= '2026-01-28';

-- Query 2: Check channel distribution in VN
SELECT
    channel,
    COUNT(DISTINCT orderNumber) AS order_count
FROM ptn_am.silver.vn_daily_orders_consolidated
WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 7 HOUR)) >= '2026-01-01'
AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 7 HOUR)) <= '2026-01-28'
GROUP BY channel
ORDER BY order_count DESC;

-- Query 3: Check vendor patterns in VN
SELECT
    COUNT(*) AS total_orders,
    SUM(CASE WHEN vendorAccountId LIKE '%BEE%' THEN 1 ELSE 0 END) AS has_BEE,
    SUM(CASE WHEN vendorAccountId LIKE '%DUM%' THEN 1 ELSE 0 END) AS has_DUM,
    SUM(CASE WHEN vendorAccountId LIKE '%#_%' ESCAPE '#' THEN 1 ELSE 0 END) AS has_underscore,
    SUM(CASE WHEN vendorAccountId NOT LIKE '%#_%' ESCAPE '#' THEN 1 ELSE 0 END) AS no_underscore
FROM ptn_am.silver.vn_daily_orders_consolidated
WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 7 HOUR)) >= '2026-01-01'
AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 7 HOUR)) <= '2026-01-28';

-- Query 4: Check status distribution in VN
SELECT
    status,
    COUNT(DISTINCT orderNumber) AS order_count
FROM ptn_am.silver.vn_daily_orders_consolidated
WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 7 HOUR)) >= '2026-01-01'
AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 7 HOUR)) <= '2026-01-28'
GROUP BY status
ORDER BY order_count DESC;

-- Query 5: Check GOLD table for VN
SELECT
    COUNT(DISTINCT order_number) AS orders,
    COUNT(DISTINCT account_id) AS buyers,
    SUM(current_total/26416) AS gmv_usd
FROM wh_am.gold.fact_orders
WHERE country = 'VN'
AND TO_DATE(placement_date) >= '2026-01-01'
AND TO_DATE(placement_date) <= '2026-01-28';

-- Query 6: Check GOLD with filters
SELECT
    COUNT(DISTINCT order_number) AS orders,
    COUNT(DISTINCT account_id) AS buyers,
    SUM(current_total/26416) AS gmv_usd
FROM wh_am.gold.fact_orders
WHERE country = 'VN'
AND TO_DATE(placement_date) >= '2026-01-01'
AND TO_DATE(placement_date) <= '2026-01-28'
AND vendor_account_id NOT LIKE '%BEE%'
AND vendor_account_id NOT LIKE '%DUM%'
AND vendor_account_id LIKE '%#_%' ESCAPE '#'
AND current_status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
AND first_channel IN ('B2B_APP', 'CX_TLP', 'B2B_WEB', 'B2B_FORCE');

-- Query 7: Sample VN vendor IDs to check pattern
SELECT DISTINCT
    vendor_account_id,
    COUNT(DISTINCT order_number) AS order_count
FROM wh_am.gold.fact_orders
WHERE country = 'VN'
AND TO_DATE(placement_date) >= '2026-01-01'
AND TO_DATE(placement_date) <= '2026-01-28'
GROUP BY vendor_account_id
ORDER BY order_count DESC
LIMIT 20;
