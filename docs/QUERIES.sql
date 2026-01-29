-- ============================================================================
-- BEES DASHBOARD - DATABRICKS SQL QUERIES
-- ============================================================================
-- This file documents all SQL queries used in the dashboard data extraction
-- Last Updated: 2026-01-29
-- Data Source: Silver tables only (ptn_am.silver.*)
-- ============================================================================

-- ============================================================================
-- 1. PHILIPPINES SILVER TABLE QUERY
-- ============================================================================
-- Purpose: Extract PH orders for all metrics (daily, MTD, historical)
-- Table: ptn_am.silver.daily_orders_consolidated
-- Time Range: Last 15 days for historical charts, MTD for month totals
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
AND channel IN ('B2B_APP', 'B2B_WEB', 'B2B_LNK', 'B2B_FORCE', 'CX_TLP')
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
-- - Channel whitelist: B2B_APP, B2B_WEB, B2B_LNK, B2B_FORCE, CX_TLP

-- ============================================================================
-- 2. VIETNAM SILVER TABLE QUERY
-- ============================================================================
-- Purpose: Extract VN orders for all metrics (daily, MTD, historical)
-- Table: ptn_am.silver.vn_daily_orders_consolidated
-- Time Range: Last 15 days for historical charts, MTD for month totals
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
AND channel IN ('B2B_APP', 'B2B_WEB', 'B2B_LNK', 'B2B_FORCE', 'CX_TLP')
AND vendorAccountId NOT LIKE '%BEE%'
AND vendorAccountId NOT LIKE '%DUM%'
AND status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
-- Optional hour filter for same-time comparisons:
-- AND HOUR(createAt + INTERVAL 7 HOUR) <= {hour_limit}
QUALIFY ROW_NUMBER() OVER(PARTITION BY orderNumber ORDER BY createAt DESC) = 1;

-- Notes:
-- - UTC+7 timezone offset for Vietnam
-- - Channel whitelist: B2B_APP, B2B_WEB, B2B_LNK, B2B_FORCE, CX_TLP
-- - Same vendor and status filters as PH (except no underscore requirement for VN)

-- ============================================================================
-- 3. VERIFICATION QUERY - PH MTD GMV
-- ============================================================================
-- Purpose: Verify MTD GMV from Silver table
-- Run this to validate dashboard calculations

SELECT
    SUM(total/56.017) AS total_gmv_usd,
    COUNT(DISTINCT orderNumber) AS total_orders,
    COUNT(DISTINCT beesAccountId) AS total_buyers
FROM ptn_am.silver.daily_orders_consolidated
WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 8 HOUR)) >= '2026-01-01'
AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 8 HOUR)) <= '2026-01-29'
AND channel IN ('B2B_APP', 'B2B_WEB', 'B2B_LNK', 'B2B_FORCE', 'CX_TLP')
AND vendorAccountId NOT LIKE '%BEE%'
AND vendorAccountId NOT LIKE '%DUM%'
AND vendorAccountId LIKE '%#_%' ESCAPE '#'
AND status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
QUALIFY ROW_NUMBER() OVER(PARTITION BY orderNumber ORDER BY createAt DESC) = 1;

-- ============================================================================
-- 4. CHANNEL BREAKDOWN QUERY - MUTUALLY EXCLUSIVE CLASSIFICATION
-- ============================================================================
-- Purpose: Calculate Grow vs Customer buyer share (mutually exclusive)
-- Logic:
--   - If buyer has ANY Customer channel orders (B2B_APP, B2B_WEB, B2B_LNK, B2B_FORCE) → Customer
--   - Else (only CX_TLP orders) → Grow
-- This ensures Grow% + Customer% = 100%

-- Step 1: Get all buyers with their channels
WITH buyer_channels AS (
    SELECT DISTINCT
        beesAccountId AS account_id,
        channel
    FROM ptn_am.silver.daily_orders_consolidated
    WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 8 HOUR)) >= '2026-01-01'
    AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 8 HOUR)) <= '2026-01-29'
    AND vendorAccountId NOT LIKE '%BEE%'
    AND vendorAccountId NOT LIKE '%DUM%'
    AND vendorAccountId LIKE '%#_%' ESCAPE '#'
    AND status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
    AND channel IN ('B2B_APP', 'B2B_WEB', 'B2B_LNK', 'B2B_FORCE', 'CX_TLP')
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
-- 5. DATA QUALITY CHECKS
-- ============================================================================

-- Check 1: Verify deduplication works
SELECT
    orderNumber,
    COUNT(*) AS duplicate_count
FROM (
    SELECT orderNumber
    FROM ptn_am.silver.daily_orders_consolidated
    WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 8 HOUR)) >= '2026-01-01'
    AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 8 HOUR)) <= '2026-01-29'
    QUALIFY ROW_NUMBER() OVER(PARTITION BY orderNumber ORDER BY createAt DESC) = 1
)
GROUP BY orderNumber
HAVING COUNT(*) > 1
LIMIT 10;
-- Expected: 0 rows (QUALIFY should handle deduplication)

-- Check 2: Verify channel values
SELECT
    channel,
    COUNT(DISTINCT orderNumber) AS order_count,
    COUNT(DISTINCT beesAccountId) AS buyer_count
FROM ptn_am.silver.daily_orders_consolidated
WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 8 HOUR)) >= '2026-01-01'
AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 8 HOUR)) <= '2026-01-29'
AND vendorAccountId NOT LIKE '%BEE%'
AND vendorAccountId NOT LIKE '%DUM%'
AND vendorAccountId LIKE '%#_%' ESCAPE '#'
AND status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
GROUP BY channel
ORDER BY order_count DESC;
-- Expected channels: B2B_APP, B2B_WEB, B2B_LNK, B2B_FORCE, CX_TLP

-- Check 3: Verify status distribution
SELECT
    status,
    COUNT(DISTINCT orderNumber) AS order_count
FROM ptn_am.silver.daily_orders_consolidated
WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 8 HOUR)) >= '2026-01-01'
AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL 8 HOUR)) <= '2026-01-29'
GROUP BY status
ORDER BY order_count DESC;
-- Should exclude: DENIED, CANCELLED, PENDING CANCELLATION

-- ============================================================================
-- 6. CURRENCY CONVERSION RATES
-- ============================================================================
-- Philippines: 1 USD = 56.017 PHP
-- Vietnam: 1 USD = 26,416 VND
-- Formula: order_total / rate = USD value

-- ============================================================================
-- 7. TIMEZONE OFFSETS
-- ============================================================================
-- Philippines (Asia/Manila): UTC+8
-- Vietnam (Asia/Ho_Chi_Minh): UTC+7
-- Hong Kong (display timezone): UTC+8

-- ============================================================================
-- 8. DATA FLOW SUMMARY
-- ============================================================================
-- ALL METRICS NOW USE SILVER TABLES:
--
-- DAILY METRICS (Today, Last Week):
--   → Silver tables (ptn_am.silver.daily_orders_consolidated, vn_daily_orders_consolidated)
--   → Hour-limited for same-time comparison
--   → Used for: Today boxes, Last week comparison, Daily charts
--
-- MTD METRICS (Month-to-Date):
--   → Silver tables (full month-to-date query)
--   → Used for: MTD boxes, MTD comparison
--
-- CHANNEL METRICS (Buyer Share):
--   → Silver tables
--   → Hour-limited to match daily comparison timing
--   → Mutually exclusive classification (Customer first, then Grow)
--   → Ensures percentages sum to 100%

-- ============================================================================
-- END OF QUERIES
-- ============================================================================
