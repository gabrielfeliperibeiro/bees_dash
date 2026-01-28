-- ============================================================================
-- BEES DASHBOARD - DATABRICKS SQL QUERIES
-- ============================================================================
-- This file documents all SQL queries used in the dashboard data extraction
-- Last Updated: 2026-01-28
-- ============================================================================

-- ============================================================================
-- 1. PHILIPPINES SILVER TABLE QUERY (Daily/Historical Data)
-- ============================================================================
-- Purpose: Extract PH orders from silver layer for daily metrics and charts
-- Table: ptn_am.silver.daily_orders_consolidated
-- Time Range: Last 15 days for historical charts, specific dates for comparisons
-- Hour Filter: Applied for same-time comparisons (e.g., today up to 10:00 vs last week at 10:00)

SELECT
    'PH' AS country,
    createAt AS placement_date,
    orderNumber AS order_number,
    total AS order_gmv,
    total/56.017 AS order_gmv_usd,
    beesAccountId AS account_id,
    vendorAccountId AS vendor_account_id,
    status AS order_status,
    channel
FROM ptn_am.silver.daily_orders_consolidated
WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 8 HOUR)) >= '{start_date}'
AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 8 HOUR)) <= '{end_date}'
AND channel NOT IN ('SALESMAN')
AND vendorAccountId NOT LIKE '%BEE%'
AND vendorAccountId NOT LIKE '%DUM%'
AND vendorAccountId LIKE '%#_%' ESCAPE '#'
AND status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
-- Optional hour filter for same-time comparisons:
-- AND HOUR(createAt + INTERVAL 8 HOUR) <= {hour_limit}
QUALIFY ROW_NUMBER() OVER(PARTITION BY orderNumber ORDER BY createAt DESC) = 1;

-- Notes:
-- - UTC+8 timezone offset for Philippines
-- - Deduplication using QUALIFY to handle append-only table
-- - Vendor filters exclude test/dummy accounts
-- - Status filters exclude cancelled/denied orders
-- - Channel filter excludes SALESMAN channel

-- ============================================================================
-- 2. VIETNAM SILVER TABLE QUERY (Daily/Historical Data)
-- ============================================================================
-- Purpose: Extract VN orders from silver layer for daily metrics and charts
-- Table: ptn_am.silver.vn_daily_orders_consolidated
-- Time Range: Last 15 days for historical charts, specific dates for comparisons
-- Hour Filter: Applied for same-time comparisons (e.g., today up to 9:00 vs last week at 9:00)

SELECT
    'VN' AS country,
    createAt AS placement_date,
    orderNumber AS order_number,
    total AS order_gmv,
    total/26416 AS order_gmv_usd,
    beesAccountId AS account_id,
    vendorAccountId AS vendor_account_id,
    status AS order_status,
    channel
FROM ptn_am.silver.vn_daily_orders_consolidated
WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 7 HOUR)) >= '{start_date}'
AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 7 HOUR)) <= '{end_date}'
AND channel NOT IN ('SALESMAN', 'NON-BEES')
AND vendorAccountId NOT LIKE '%BEE%'
AND vendorAccountId NOT LIKE '%DUM%'
AND vendorAccountId LIKE '%#_%' ESCAPE '#'
AND status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
-- Optional hour filter for same-time comparisons:
-- AND HOUR(createAt + INTERVAL 7 HOUR) <= {hour_limit}
QUALIFY ROW_NUMBER() OVER(PARTITION BY orderNumber ORDER BY createAt DESC) = 1;

-- Notes:
-- - UTC+7 timezone offset for Vietnam
-- - Additional filter: excludes 'NON-BEES' channel
-- - Same vendor and status filters as PH

-- ============================================================================
-- 3. PHILIPPINES GOLD TABLE QUERY (MTD Historical Data D-1 and earlier)
-- ============================================================================
-- Purpose: Extract PH orders from GOLD layer for accurate MTD calculations
-- Table: wh_am.gold.fact_orders
-- Time Range: Month start to yesterday (D-1)
-- Usage: Combined with today's silver data for complete MTD metrics

SELECT
    'PH' AS country,
    placement_date,
    order_number,
    current_total AS order_gmv,
    current_total/56.017 AS order_gmv_usd,
    account_id,
    vendor_account_id,
    current_status AS order_status,
    first_channel AS channel
FROM wh_am.gold.fact_orders
WHERE country = 'PH'
AND TO_DATE(placement_date) >= '{start_date}'
AND TO_DATE(placement_date) <= '{end_date}'
AND vendor_account_id NOT LIKE '%BEE%'
AND vendor_account_id NOT LIKE '%DUM%'
AND vendor_account_id LIKE '%#_%' ESCAPE '#'
AND current_status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
AND first_channel IN ('B2B_APP', 'CX_TLP', 'B2B_WEB', 'B2B_FORCE');

-- Notes:
-- - Uses current_total (not total) for GMV
-- - Uses current_status (not status)
-- - Uses first_channel (not channel)
-- - Channel whitelist instead of blacklist
-- - No QUALIFY needed (GOLD is already deduplicated)
-- - Combined with today's silver data to get complete MTD

-- ============================================================================
-- 4. VIETNAM GOLD TABLE QUERY (MTD Historical Data D-1 and earlier)
-- ============================================================================
-- Purpose: Extract VN orders from GOLD layer for accurate MTD calculations
-- Table: wh_am.gold.fact_orders
-- Time Range: Month start to yesterday (D-1)
-- Usage: Combined with today's silver data for complete MTD metrics

SELECT
    'VN' AS country,
    placement_date,
    order_number,
    current_total AS order_gmv,
    current_total/26416 AS order_gmv_usd,
    account_id,
    vendor_account_id,
    current_status AS order_status,
    first_channel AS channel
FROM wh_am.gold.fact_orders
WHERE country = 'VN'
AND TO_DATE(placement_date) >= '{start_date}'
AND TO_DATE(placement_date) <= '{end_date}'
AND vendor_account_id NOT LIKE '%BEE%'
AND vendor_account_id NOT LIKE '%DUM%'
AND vendor_account_id LIKE '%#_%' ESCAPE '#'
AND current_status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
AND first_channel IN ('B2B_APP', 'CX_TLP', 'B2B_WEB', 'B2B_FORCE');

-- Notes:
-- - Same structure as PH GOLD query
-- - Different currency conversion rate (VND: 26,416)
-- - Combined with today's silver data to get complete MTD

-- ============================================================================
-- 5. VERIFICATION QUERY - PH MTD GMV (User's Source of Truth)
-- ============================================================================
-- Purpose: Verify MTD GMV matches expected value from GOLD table
-- Expected Result: ~$2.5M+ for January 2026
-- Run this to validate dashboard calculations

SELECT
    SUM(current_total/56.017) AS total_gmv_usd,
    COUNT(DISTINCT order_number) AS total_orders,
    COUNT(DISTINCT account_id) AS total_buyers
FROM wh_am.gold.fact_orders
WHERE country = 'PH'
AND TO_DATE(placement_date) >= '2026-01-01'
AND TO_DATE(placement_date) <= '2026-01-28'
AND vendor_account_id NOT LIKE '%BEE%'
AND vendor_account_id NOT LIKE '%DUM%'
AND vendor_account_id LIKE '%#_%' ESCAPE '#'
AND current_status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
AND first_channel IN ('B2B_APP', 'CX_TLP', 'B2B_WEB', 'B2B_FORCE');

-- Expected Output (as of 2026-01-28):
-- total_gmv_usd: ~2,565,000
-- total_orders: ~123,000
-- total_buyers: ~90,000

-- ============================================================================
-- 6. CHANNEL BREAKDOWN QUERY - MUTUALLY EXCLUSIVE CLASSIFICATION
-- ============================================================================
-- Purpose: Calculate Grow vs Customer buyer share (mutually exclusive)
-- Logic:
--   - If buyer has ANY Customer channel orders (B2B_APP, B2B_WEB, B2B_FORCE) → Customer
--   - Else (only CX_TLP orders) → Grow
-- This ensures Grow% + Customer% = 100%

-- Step 1: Get all buyers with their channels
WITH buyer_channels AS (
    SELECT DISTINCT
        account_id,
        first_channel AS channel
    FROM wh_am.gold.fact_orders
    WHERE country = 'PH'
    AND TO_DATE(placement_date) >= '2026-01-01'
    AND TO_DATE(placement_date) <= '2026-01-28'
    AND vendor_account_id NOT LIKE '%BEE%'
    AND vendor_account_id NOT LIKE '%DUM%'
    AND vendor_account_id LIKE '%#_%' ESCAPE '#'
    AND current_status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
    AND first_channel IN ('B2B_APP', 'CX_TLP', 'B2B_WEB', 'B2B_FORCE')
),
-- Step 2: Classify buyers (Customer first, then Grow)
buyer_classification AS (
    SELECT
        account_id,
        CASE
            WHEN SUM(CASE WHEN channel != 'CX_TLP' THEN 1 ELSE 0 END) > 0 THEN 'Customer'
            ELSE 'Grow'
        END AS buyer_type
    FROM buyer_channels
    GROUP BY account_id
)
-- Step 3: Calculate percentages
SELECT
    buyer_type,
    COUNT(DISTINCT account_id) AS buyer_count,
    ROUND(COUNT(DISTINCT account_id) * 100.0 / SUM(COUNT(DISTINCT account_id)) OVER(), 1) AS buyer_percent
FROM buyer_classification
GROUP BY buyer_type;

-- Expected Output:
-- Grow: ~50,000 buyers (~52-56%)
-- Customer: ~43,000 buyers (~44-48%)
-- Sum: 100.0%

-- ============================================================================
-- 7. DATA QUALITY CHECKS
-- ============================================================================

-- Check 1: Verify no duplicate orders in GOLD
SELECT
    order_number,
    COUNT(*) AS duplicate_count
FROM wh_am.gold.fact_orders
WHERE country = 'PH'
AND TO_DATE(placement_date) >= '2026-01-01'
AND TO_DATE(placement_date) <= '2026-01-28'
GROUP BY order_number
HAVING COUNT(*) > 1
LIMIT 10;
-- Expected: 0 rows (GOLD should have no duplicates)

-- Check 2: Verify channel values
SELECT
    first_channel,
    COUNT(DISTINCT order_number) AS order_count,
    COUNT(DISTINCT account_id) AS buyer_count
FROM wh_am.gold.fact_orders
WHERE country = 'PH'
AND TO_DATE(placement_date) >= '2026-01-01'
AND TO_DATE(placement_date) <= '2026-01-28'
AND vendor_account_id NOT LIKE '%BEE%'
AND vendor_account_id NOT LIKE '%DUM%'
AND vendor_account_id LIKE '%#_%' ESCAPE '#'
AND current_status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
GROUP BY first_channel
ORDER BY order_count DESC;
-- Expected channels: B2B_APP, CX_TLP, B2B_WEB, B2B_FORCE

-- Check 3: Verify status distribution
SELECT
    current_status,
    COUNT(DISTINCT order_number) AS order_count
FROM wh_am.gold.fact_orders
WHERE country = 'PH'
AND TO_DATE(placement_date) >= '2026-01-01'
AND TO_DATE(placement_date) <= '2026-01-28'
GROUP BY current_status
ORDER BY order_count DESC;
-- Should exclude: DENIED, CANCELLED, PENDING CANCELLATION

-- ============================================================================
-- 8. CURRENCY CONVERSION RATES
-- ============================================================================
-- Philippines: 1 USD = 56.017 PHP
-- Vietnam: 1 USD = 26,416 VND
-- Formula: order_total / rate = USD value

-- ============================================================================
-- 9. TIMEZONE OFFSETS
-- ============================================================================
-- Philippines (Asia/Manila): UTC+8
-- Vietnam (Asia/Ho_Chi_Minh): UTC+7
-- Hong Kong (display timezone): UTC+8

-- ============================================================================
-- 10. DATA FLOW SUMMARY
-- ============================================================================
-- DAILY METRICS (Today, Last Week):
--   → Silver tables (ptn_am.silver.daily_orders_consolidated, vn_daily_orders_consolidated)
--   → Hour-limited for same-time comparison
--   → Used for: Today boxes, Last week comparison, Daily charts

-- MTD METRICS (Month-to-Date):
--   → GOLD table (wh_am.gold.fact_orders) for D-1 and earlier
--   → Silver table for today (full day, not hour-limited)
--   → Merged and deduplicated on order_number
--   → Used for: MTD boxes, MTD comparison

-- CHANNEL METRICS (Buyer Share):
--   → GOLD table for today (silver may not have channel populated yet)
--   → Hour-limited to match daily comparison timing
--   → Mutually exclusive classification (Customer first, then Grow)
--   → Ensures percentages sum to 100%

-- ============================================================================
-- END OF QUERIES
-- ============================================================================
