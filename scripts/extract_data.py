"""Extract sales data from Databricks and generate JSON files."""
import sys
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from databricks import sql
import pandas as pd

from config import (
    DATABRICKS_SERVER_HOSTNAME,
    DATABRICKS_HTTP_PATH,
    DATABRICKS_TOKEN,
    COUNTRIES,
    CURRENCY_RATES,
    TIMEZONES,
    DATA_DIR,
    LOGS_DIR,
    get_today,
    get_same_day_last_week,
    get_mtd_start,
    get_last_month_mtd_range,
    get_hk_time,
    get_hk_now_utc,
)

# Setup logging
Path(LOGS_DIR).mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"{LOGS_DIR}/extract_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def connect_to_databricks(max_retries=3, retry_delay_seconds=[0, 10, 20]):
    """
    Connect to Databricks with retry logic.

    Attempts connection 3 times within 30 seconds:
    - Attempt 1: Immediate
    - Attempt 2: After 10 seconds
    - Attempt 3: After 20 seconds (total 30s window)
    """
    import time

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(retry_delay_seconds[attempt])

            logger.info(f"Connecting to Databricks (attempt {attempt + 1}/{max_retries})...")
            connection = sql.connect(
                server_hostname=DATABRICKS_SERVER_HOSTNAME,
                http_path=DATABRICKS_HTTP_PATH,
                access_token=DATABRICKS_TOKEN,
            )
            logger.info("Successfully connected to Databricks")
            return connection
        except Exception as e:
            logger.error(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.error("All connection attempts failed")
                raise

    return None


def query_gold_orders(connection, country, start_date, end_date):
    """
    Query historical orders from GOLD fact table (for D-1 and earlier).

    Args:
        connection: Databricks connection
        country: Country code (PH or VN)
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        pandas DataFrame with order data
    """
    logger.info(f"[GOLD] Querying {country} from {start_date} to {end_date}")

    if country == 'PH':
        query = f"""
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
        AND first_channel IN ('B2B_APP', 'CX_TLP', 'B2B_WEB', 'B2B_FORCE')
        """
    else:  # VN
        query = f"""
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
        AND first_channel IN ('B2B_APP', 'CX_TLP', 'B2B_WEB', 'B2B_FORCE')
        """

    try:
        cursor = connection.cursor()
        cursor.execute(query)

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        if not rows:
            logger.warning(f"[GOLD] No data returned for {country}")
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=columns)
        logger.info(f"[GOLD] Retrieved {len(df)} orders for {country}")

        cursor.close()
        return df

    except Exception as e:
        logger.error(f"[GOLD] Query failed for {country}: {e}")
        raise


def query_orders(connection, country, start_date, end_date, hour_limit=None):
    """
    Query orders from Databricks silver layer for a specific country and date range.

    Args:
        connection: Databricks connection
        country: Country code (PH or VN)
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        hour_limit: Optional hour limit (0-23) for same-time comparisons

    Returns:
        pandas DataFrame with order data
    """
    # Timezone offset for each country
    tz_offset = 8 if country == 'PH' else 7  # PH: UTC+8, VN: UTC+7

    # Build hour filter if provided
    hour_filter = ""
    if hour_limit is not None:
        hour_filter = f"AND HOUR(createAt + INTERVAL {tz_offset} HOUR) <= {hour_limit}"

    # Build query based on country for silver tables
    # Use QUALIFY to deduplicate append-only table data
    # Exclude SALESMAN channel from analysis
    if country == 'PH':
        query = f"""
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
        WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL {tz_offset} HOUR)) >= '{start_date}'
        AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL {tz_offset} HOUR)) <= '{end_date}'
        AND channel NOT IN ('SALESMAN')
        AND vendorAccountId NOT LIKE '%BEE%'
        AND vendorAccountId NOT LIKE '%DUM%'
        AND vendorAccountId LIKE '%#_%' ESCAPE '#'
        AND status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
        {hour_filter}
        QUALIFY ROW_NUMBER() OVER(PARTITION BY orderNumber ORDER BY createAt DESC) = 1
        """
    else:  # VN
        query = f"""
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
        WHERE TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL {tz_offset} HOUR)) >= '{start_date}'
        AND TO_DATE(DATE_TRUNC('DAY', createAt + INTERVAL {tz_offset} HOUR)) <= '{end_date}'
        AND channel NOT IN ('SALESMAN', 'NON-BEES')
        AND vendorAccountId NOT LIKE '%BEE%'
        AND vendorAccountId NOT LIKE '%DUM%'
        AND vendorAccountId LIKE '%#_%' ESCAPE '#'
        AND status NOT IN ('DENIED', 'CANCELLED', 'PENDING CANCELLATION')
        {hour_filter}
        QUALIFY ROW_NUMBER() OVER(PARTITION BY orderNumber ORDER BY createAt DESC) = 1
        """

    logger.info(f"Querying orders for {country} from {start_date} to {end_date}")

    try:
        cursor = connection.cursor()
        cursor.execute(query)

        # Fetch results
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        if not rows:
            logger.warning(f"No data returned for {country}")
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=columns)
        logger.info(f"Retrieved {len(df)} orders for {country}")

        cursor.close()
        return df

    except Exception as e:
        logger.error(f"Query failed for {country}: {e}")
        raise


def calculate_metrics(df, country=None):
    """
    Calculate sales metrics from order data.

    Args:
        df: pandas DataFrame with order data
        country: Country code (PH or VN) for USD conversion

    Returns:
        dict with calculated metrics
    """
    if df.empty:
        return {
            "total_gmv": 0,
            "total_gmv_usd": 0,
            "orders": 0,
            "unique_buyers": 0,
            "unique_vendors": 0,
            "aov": 0,
            "aov_usd": 0,
            "frequency": 0,
            "gmv_per_poc": 0,
            "gmv_per_poc_usd": 0,
        }

    # Convert numeric columns to proper types (Databricks may return strings)
    df["order_gmv"] = pd.to_numeric(df["order_gmv"], errors='coerce')

    total_gmv = df["order_gmv"].sum()
    orders = df["order_number"].nunique()
    unique_buyers = df["account_id"].nunique()
    unique_vendors = df["vendor_account_id"].nunique()

    # Calculate derived metrics
    aov = total_gmv / orders if orders > 0 else 0
    frequency = orders / unique_buyers if unique_buyers > 0 else 0
    gmv_per_poc = total_gmv / unique_vendors if unique_vendors > 0 else 0

    # Calculate USD values
    usd_rate = CURRENCY_RATES.get(country, 1) if country else 1
    total_gmv_usd = total_gmv / usd_rate
    aov_usd = aov / usd_rate
    gmv_per_poc_usd = gmv_per_poc / usd_rate

    return {
        "total_gmv": round(total_gmv, 2),
        "total_gmv_usd": round(total_gmv_usd, 2),
        "orders": orders,
        "unique_buyers": unique_buyers,
        "unique_vendors": unique_vendors,
        "aov": round(aov, 2),
        "aov_usd": round(aov_usd, 2),
        "frequency": round(frequency, 2),
        "gmv_per_poc": round(gmv_per_poc, 2),
        "gmv_per_poc_usd": round(gmv_per_poc_usd, 2),
    }


def calculate_channel_metrics(df, country=None):
    """
    Calculate channel breakdown metrics (Customer vs CX_TLP).

    Customer channels: B2B_APP, B2B_WEB, B2B_FORCE (not CX_TLP)
    Grow channel: CX_TLP

    Args:
        df: pandas DataFrame with order data including channel column
        country: Country code (PH or VN) for USD conversion

    Returns:
        dict with channel breakdown metrics including buyer counts
    """
    if df.empty or 'channel' not in df.columns:
        return {
            "customer": {"gmv_usd": 0, "orders": 0, "buyers": 0, "gmv_percent": 0, "orders_percent": 0, "buyers_percent": 0},
            "cx_tlp": {"gmv_usd": 0, "orders": 0, "buyers": 0, "gmv_percent": 0, "orders_percent": 0, "buyers_percent": 0}
        }

    # Create explicit copy to avoid SettingWithCopyWarning
    df = df.copy()

    # Convert numeric columns
    df["order_gmv"] = pd.to_numeric(df["order_gmv"], errors='coerce')
    usd_rate = CURRENCY_RATES.get(country, 1) if country else 1

    # Total metrics
    total_gmv = df["order_gmv"].sum()
    total_gmv_usd = total_gmv / usd_rate
    total_orders = df["order_number"].nunique()
    total_buyers = df["account_id"].nunique()

    # Customer channels (B2B_APP, B2B_WEB, B2B_FORCE - not CX_TLP)
    df_customer = df[df["channel"] != "CX_TLP"]
    customer_gmv = df_customer["order_gmv"].sum()
    customer_gmv_usd = customer_gmv / usd_rate
    customer_orders = df_customer["order_number"].nunique()
    customer_buyers = df_customer["account_id"].nunique()

    # CX_TLP channel (Grow)
    df_cx_tlp = df[df["channel"] == "CX_TLP"]
    cx_tlp_gmv = df_cx_tlp["order_gmv"].sum()
    cx_tlp_gmv_usd = cx_tlp_gmv / usd_rate
    cx_tlp_orders = df_cx_tlp["order_number"].nunique()
    cx_tlp_buyers = df_cx_tlp["account_id"].nunique()

    # Calculate percentages
    customer_gmv_pct = (customer_gmv_usd / total_gmv_usd * 100) if total_gmv_usd > 0 else 0
    customer_orders_pct = (customer_orders / total_orders * 100) if total_orders > 0 else 0
    customer_buyers_pct = (customer_buyers / total_buyers * 100) if total_buyers > 0 else 0

    cx_tlp_gmv_pct = (cx_tlp_gmv_usd / total_gmv_usd * 100) if total_gmv_usd > 0 else 0
    cx_tlp_orders_pct = (cx_tlp_orders / total_orders * 100) if total_orders > 0 else 0
    cx_tlp_buyers_pct = (cx_tlp_buyers / total_buyers * 100) if total_buyers > 0 else 0

    return {
        "customer": {
            "gmv_usd": round(customer_gmv_usd, 2),
            "orders": customer_orders,
            "buyers": customer_buyers,
            "gmv_percent": round(customer_gmv_pct, 1),
            "orders_percent": round(customer_orders_pct, 1),
            "buyers_percent": round(customer_buyers_pct, 1)
        },
        "cx_tlp": {
            "gmv_usd": round(cx_tlp_gmv_usd, 2),
            "orders": cx_tlp_orders,
            "buyers": cx_tlp_buyers,
            "gmv_percent": round(cx_tlp_gmv_pct, 1),
            "orders_percent": round(cx_tlp_orders_pct, 1),
            "buyers_percent": round(cx_tlp_buyers_pct, 1)
        }
    }


def calculate_daily_metrics(df, country=None):
    """
    Calculate metrics grouped by day.

    Args:
        df: pandas DataFrame with order data
        country: Country code (PH or VN) for USD conversion

    Returns:
        list of dicts with daily metrics
    """
    if df.empty:
        return []

    # Create explicit copy to avoid SettingWithCopyWarning
    df = df.copy()

    # Convert placement_date to date (handle mixed ISO8601 formats)
    df["date"] = pd.to_datetime(df["placement_date"], format='mixed', utc=True).dt.date

    daily_metrics = []
    for date, group in df.groupby("date"):
        metrics = calculate_metrics(group, country)
        metrics["date"] = str(date)
        daily_metrics.append(metrics)

    # Sort by date
    daily_metrics.sort(key=lambda x: x["date"])

    return daily_metrics


def calculate_moving_average(daily_metrics, window):
    """
    Calculate moving average for metrics.

    Args:
        daily_metrics: list of daily metric dicts
        window: number of days for moving average

    Returns:
        dict with moving average metrics
    """
    if len(daily_metrics) < window:
        logger.warning(f"Not enough data for {window}-day moving average")
        window = len(daily_metrics)

    if window == 0:
        return {
            "gmv": 0,
            "orders": 0,
            "aov": 0,
            "unique_buyers": 0,
            "frequency": 0,
            "gmv_per_poc": 0,
        }

    # Get last N days
    recent_data = daily_metrics[-window:]

    # Calculate averages (use USD values for monetary metrics)
    avg_gmv = sum(d.get("total_gmv_usd", d.get("total_gmv", 0)) for d in recent_data) / window
    avg_orders = sum(d["orders"] for d in recent_data) / window
    avg_aov = sum(d.get("aov_usd", d.get("aov", 0)) for d in recent_data) / window
    avg_buyers = sum(d["unique_buyers"] for d in recent_data) / window
    avg_frequency = sum(d["frequency"] for d in recent_data) / window
    avg_gmv_per_poc = sum(d.get("gmv_per_poc_usd", d.get("gmv_per_poc", 0)) for d in recent_data) / window

    return {
        "gmv": round(avg_gmv, 2),
        "orders": round(avg_orders, 2),
        "aov": round(avg_aov, 2),
        "unique_buyers": round(avg_buyers, 2),
        "frequency": round(avg_frequency, 2),
        "gmv_per_poc": round(avg_gmv_per_poc, 2),
    }


def generate_json_output(country, metrics_today, metrics_last_week, metrics_mtd, metrics_mtd_last_month, daily_metrics, ma_7d, ma_15d, channel_metrics_today=None, channel_metrics_last_week=None, channel_metrics_mtd=None, channel_metrics_mtd_last_month=None):
    """
    Generate JSON output structure for a country.

    Args:
        country: Country code
        metrics_today: Today's metrics dict
        metrics_last_week: Same day last week metrics dict
        metrics_mtd: Month-to-date metrics dict
        metrics_mtd_last_month: Last month MTD metrics dict
        daily_metrics: List of daily metrics dicts
        ma_7d: 7-day moving average dict
        ma_15d: 15-day moving average dict
        channel_metrics_today: Today's channel breakdown dict
        channel_metrics_last_week: Last week same day channel breakdown dict
        channel_metrics_mtd: MTD channel breakdown dict
        channel_metrics_mtd_last_month: Last month MTD channel breakdown dict

    Returns:
        dict ready for JSON serialization
    """
    today = get_today()
    same_day_last_week = get_same_day_last_week()
    mtd_start = get_mtd_start()
    last_month_mtd_start, last_month_mtd_end = get_last_month_mtd_range()

    output = {
        "last_updated": datetime.now().isoformat() + "Z",
        "today": {
            "date": str(today),
            **metrics_today
        },
        "same_day_last_week": {
            "date": str(same_day_last_week),
            **metrics_last_week
        },
        "mtd": {
            "start_date": str(mtd_start),
            "end_date": str(today),
            **metrics_mtd
        },
        "mtd_last_month": {
            "start_date": str(last_month_mtd_start),
            "end_date": str(last_month_mtd_end),
            **metrics_mtd_last_month
        },
        "daily_history": daily_metrics,
        "moving_averages": {
            "ma_7d": ma_7d,
            "ma_15d": ma_15d
        }
    }

    # Add channel metrics if available
    if channel_metrics_today:
        output["channel_breakdown_today"] = channel_metrics_today
    if channel_metrics_last_week:
        output["channel_breakdown_last_week"] = channel_metrics_last_week
    if channel_metrics_mtd:
        output["channel_breakdown_mtd"] = channel_metrics_mtd
    if channel_metrics_mtd_last_month:
        output["channel_breakdown_mtd_last_month"] = channel_metrics_mtd_last_month

    return output


def save_json_file(data, country):
    """
    Save data to JSON file with versioning.

    Args:
        data: Data dict to save
        country: Country code for filename
    """
    Path(DATA_DIR).mkdir(exist_ok=True)

    # Save versioned file with timestamp
    timestamp = int(datetime.now(timezone.utc).timestamp())
    versioned_filename = f"{DATA_DIR}/{country.lower()}-{timestamp}.json"

    # Also save to regular filename for backward compatibility
    regular_filename = f"{DATA_DIR}/{country.lower()}.json"

    try:
        # Save versioned file
        with open(versioned_filename, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved versioned data to {versioned_filename}")

        # Save regular file
        with open(regular_filename, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved data to {regular_filename}")

        return versioned_filename
    except Exception as e:
        logger.error(f"Failed to save data: {e}")
        raise


def cleanup_old_versions(keep_versions=5):
    """
    Clean up old versioned data files, keeping only the most recent versions.

    Args:
        keep_versions: Number of recent versions to keep (default: 5)
    """
    logger.info(f"Cleaning up old versioned files (keeping {keep_versions} versions)...")

    for country in COUNTRIES:
        country_lower = country.lower()
        pattern = f"{DATA_DIR}/{country_lower}-*.json"

        # Find all versioned files for this country
        versioned_files = []
        for filepath in Path(DATA_DIR).glob(f"{country_lower}-*.json"):
            # Extract timestamp from filename (e.g., ph-1769057744.json -> 1769057744)
            filename = filepath.name
            try:
                timestamp_str = filename.replace(f"{country_lower}-", "").replace(".json", "")
                timestamp = int(timestamp_str)
                versioned_files.append((timestamp, filepath))
            except ValueError:
                # Skip files that don't match the versioned pattern
                continue

        # Sort by timestamp (newest first)
        versioned_files.sort(reverse=True, key=lambda x: x[0])

        # Keep only the most recent versions
        files_to_delete = versioned_files[keep_versions:]

        # Delete old versions
        for timestamp, filepath in files_to_delete:
            try:
                filepath.unlink()
                logger.info(f"Deleted old version: {filepath.name}")
            except Exception as e:
                logger.warning(f"Failed to delete {filepath.name}: {e}")

        if files_to_delete:
            logger.info(f"{country} - Deleted {len(files_to_delete)} old version(s)")
        else:
            logger.info(f"{country} - No old versions to delete")


def main():
    """Main execution function."""
    logger.info("Starting data extraction...")

    try:
        # Connect to Databricks
        connection = connect_to_databricks()

        # Calculate date ranges
        today = get_today()
        same_day_last_week = get_same_day_last_week()
        mtd_start = get_mtd_start()
        last_month_mtd_start, last_month_mtd_end = get_last_month_mtd_range()
        history_start = today - timedelta(days=15)

        # Track versioned filenames for manifest
        manifest = {}

        for country in COUNTRIES:
            logger.info(f"Processing {country}...")

            # Get current hour in country's timezone for same-time comparison
            country_tz = TIMEZONES.get(country)
            current_time = datetime.now(country_tz)
            current_hour = current_time.hour

            logger.info(f"{country} - Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} ({country_tz})")
            logger.info(f"{country} - Using hour limit: {current_hour} for same-time comparison")

            # Query all data needed (last 15 days) - no hour filter
            df_all = query_orders(connection, country, history_start, today)

            # Query today's data with hour limit (up to current hour)
            df_today_limited = query_orders(connection, country, today, today, hour_limit=current_hour)

            # Query last week data with same hour limit
            df_last_week = query_orders(connection, country, same_day_last_week, same_day_last_week, hour_limit=current_hour)

            # Query last month MTD data (same date range but one month ago)
            df_mtd_last_month = query_orders(connection, country, last_month_mtd_start, last_month_mtd_end)

            # Query GOLD for MTD historical (D-1 and earlier) - use yesterday as end date
            yesterday = today - timedelta(days=1)
            df_mtd_gold = pd.DataFrame()
            if mtd_start < today:
                df_mtd_gold = query_gold_orders(connection, country, mtd_start, yesterday)
                logger.info(f"{country} - MTD GOLD ({mtd_start} to {yesterday}): {len(df_mtd_gold)} orders")

            # Also query GOLD for today (with full data) for channel metrics
            # Silver may not have channel populated yet for today's orders
            df_today_gold = query_gold_orders(connection, country, today, today)
            logger.info(f"{country} - Today GOLD (full day): {len(df_today_gold)} orders")

            logger.info(f"{country} - Today (up to {current_hour}:00): {len(df_today_limited)} orders")
            logger.info(f"{country} - Last week (up to {current_hour}:00): {len(df_last_week)} orders")
            logger.info(f"{country} - Last month MTD ({last_month_mtd_start} to {last_month_mtd_end}): {len(df_mtd_last_month)} orders")

            if df_all.empty:
                logger.warning(f"No data for {country}, creating empty output...")
                # Create empty structure
                empty_metrics = calculate_metrics(pd.DataFrame(), country)
                data = generate_json_output(
                    country,
                    empty_metrics,
                    empty_metrics,
                    empty_metrics,
                    empty_metrics,
                    [],
                    empty_metrics,
                    empty_metrics,
                )
                versioned_file = save_json_file(data, country)
                manifest[country.lower()] = versioned_file.split('/')[-1]
                continue

            # Filter for different time periods (handle mixed ISO8601 formats)
            df_all["date"] = pd.to_datetime(df_all["placement_date"], format='mixed', utc=True).dt.date

            df_today_full = df_all[df_all["date"] == today]

            # Merge GOLD (D-1) + Silver (today) for complete MTD
            # Use full today data (not hour-limited) for MTD calculation
            if not df_mtd_gold.empty:
                # Ensure consistent column types before merging
                df_mtd_gold["date"] = pd.to_datetime(df_mtd_gold["placement_date"], format='mixed', utc=True).dt.date

                # Combine GOLD + today's full silver data
                df_mtd = pd.concat([df_mtd_gold, df_today_full], ignore_index=True)

                # Deduplicate on order_number to avoid double counting
                df_mtd = df_mtd.drop_duplicates(subset=['order_number'], keep='first')
                logger.info(f"{country} - Combined MTD (GOLD + today) after deduplication: {len(df_mtd)} orders")
            else:
                # Fallback to silver only if no GOLD data
                df_mtd = df_all[df_all["date"] >= mtd_start]

            # Calculate metrics using hour-limited data for fair comparison
            metrics_today = calculate_metrics(df_today_limited, country)
            metrics_last_week = calculate_metrics(df_last_week, country)
            metrics_mtd = calculate_metrics(df_mtd, country)
            metrics_mtd_last_month = calculate_metrics(df_mtd_last_month, country)

            logger.info(f"{country} - MTD GMV: ${metrics_mtd['total_gmv_usd']:,.2f}, Orders: {metrics_mtd['orders']:,}")

            # Calculate daily history
            daily_metrics = calculate_daily_metrics(df_all, country)

            # Replace today's entry with hour-limited data to match the boxes
            today_str = today.strftime('%Y-%m-%d')
            today_daily_metric = {
                "total_gmv": metrics_today["total_gmv"],
                "total_gmv_usd": metrics_today["total_gmv_usd"],
                "orders": metrics_today["orders"],
                "unique_buyers": metrics_today["unique_buyers"],
                "unique_vendors": metrics_today["unique_vendors"],
                "aov": metrics_today["aov"],
                "aov_usd": metrics_today["aov_usd"],
                "frequency": metrics_today["frequency"],
                "gmv_per_poc": metrics_today["gmv_per_poc"],
                "gmv_per_poc_usd": metrics_today["gmv_per_poc_usd"],
                "date": today_str
            }

            # Find and replace today's entry in daily_metrics
            for i, metric in enumerate(daily_metrics):
                if metric["date"] == today_str:
                    daily_metrics[i] = today_daily_metric
                    logger.info(f"{country} - Updated today's chart data to match hour-limited boxes ({metrics_today['orders']} orders)")
                    break

            # Calculate moving averages
            ma_7d = calculate_moving_average(daily_metrics, 7)
            ma_15d = calculate_moving_average(daily_metrics, 15)

            # Calculate channel metrics
            # Use GOLD data for today's channels (silver may not have channel populated yet)
            # Filter by hour to match the hour-limited comparison
            if not df_today_gold.empty:
                df_today_gold["placement_date"] = pd.to_datetime(df_today_gold["placement_date"], format='mixed', utc=True)
                df_today_gold_limited = df_today_gold[
                    df_today_gold["placement_date"].dt.hour <= current_hour
                ].copy()
                logger.info(f"{country} - Today GOLD hour-limited ({current_hour}:00): {len(df_today_gold_limited)} orders")
                channel_metrics_today = calculate_channel_metrics(df_today_gold_limited, country)
            else:
                # Fallback to silver if GOLD has no data
                channel_metrics_today = calculate_channel_metrics(df_today_limited, country)

            channel_metrics_last_week = calculate_channel_metrics(df_last_week, country)
            channel_metrics_mtd = calculate_channel_metrics(df_mtd, country)
            channel_metrics_mtd_last_month = calculate_channel_metrics(df_mtd_last_month, country)

            # Generate and save JSON
            data = generate_json_output(
                country,
                metrics_today,
                metrics_last_week,
                metrics_mtd,
                metrics_mtd_last_month,
                daily_metrics,
                ma_7d,
                ma_15d,
                channel_metrics_today,
                channel_metrics_last_week,
                channel_metrics_mtd,
                channel_metrics_mtd_last_month,
            )
            versioned_file = save_json_file(data, country)
            manifest[country.lower()] = versioned_file.split('/')[-1]

            logger.info(f"{country} - Today GMV: {metrics_today['total_gmv']}, Orders: {metrics_today['orders']}")
            logger.info(f"{country} - Last week (same time) GMV: {metrics_last_week['total_gmv']}, Orders: {metrics_last_week['orders']}")

        # Save manifest with versioned filenames
        manifest_file = f"{DATA_DIR}/data-manifest.json"
        manifest_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files": manifest
        }
        with open(manifest_file, "w") as f:
            json.dump(manifest_data, f, indent=2)
        logger.info(f"Saved manifest to {manifest_file}")

        # Clean up old versioned files
        cleanup_old_versions(keep_versions=5)

        connection.close()
        logger.info("Data extraction completed successfully")

    except Exception as e:
        logger.error(f"Data extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
