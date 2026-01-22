"""Extract sales data from Databricks and generate JSON files."""
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

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


def query_orders(connection, country, start_date, end_date, end_time=None):
    """
    Query orders from Databricks for a specific country and date range.

    Args:
        connection: Databricks connection
        country: Country code (PH or VN)
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        end_time: Optional end time (for same-time-last-week comparisons)

    Returns:
        pandas DataFrame with order data
    """
    # Timezone offset for each country
    tz_offset = 8 if country == 'PH' else 7  # PH: UTC+8, VN: UTC+7

    # Build time filter if end_time provided
    time_filter = ""
    if end_time:
        time_filter = f"AND placementDate + INTERVAL {tz_offset} HOUR <= '{end_time}'"

    # Build query based on country for production tables
    # Use QUALIFY to deduplicate append-only table data
    # Exclude SALESMAN channel from analysis
    if country == 'PH':
        query = f"""
        SELECT
            'PH' AS country,
            placementDate AS placement_date,
            orderNumber AS order_number,
            total AS order_gmv,
            total/56.017 AS order_gmv_usd,
            beesAccountId AS account_id,
            vendorAccountId AS vendor_account_id,
            status AS order_status,
            channel
        FROM ptn_am.silver.daily_orders_consolidated
        WHERE TO_DATE(DATE_TRUNC('DAY', placementDate + INTERVAL {tz_offset} HOUR)) >= '{start_date}'
        AND TO_DATE(DATE_TRUNC('DAY', placementDate + INTERVAL {tz_offset} HOUR)) <= '{end_date}'
        AND channel != 'SALESMAN'
        {time_filter}
        QUALIFY ROW_NUMBER() OVER(PARTITION BY orderNumber ORDER BY load_timestamp_utc DESC) = 1
        """
    else:  # VN
        query = f"""
        SELECT
            'VN' AS country,
            placementDate AS placement_date,
            orderNumber AS order_number,
            total AS order_gmv,
            total/26416 AS order_gmv_usd,
            beesAccountId AS account_id,
            vendorAccountId AS vendor_account_id,
            status AS order_status,
            channel
        FROM ptn_am.silver.vn_daily_orders_consolidated
        WHERE TO_DATE(DATE_TRUNC('DAY', placementDate + INTERVAL {tz_offset} HOUR)) >= '{start_date}'
        AND TO_DATE(DATE_TRUNC('DAY', placementDate + INTERVAL {tz_offset} HOUR)) <= '{end_date}'
        AND channel != 'SALESMAN'
        {time_filter}
        QUALIFY ROW_NUMBER() OVER(PARTITION BY orderNumber ORDER BY load_timestamp_utc DESC) = 1
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

    Args:
        df: pandas DataFrame with order data including channel column
        country: Country code (PH or VN) for USD conversion

    Returns:
        dict with channel breakdown metrics
    """
    if df.empty or 'channel' not in df.columns:
        return {
            "customer": {"gmv_usd": 0, "orders": 0, "gmv_percent": 0, "orders_percent": 0},
            "cx_tlp": {"gmv_usd": 0, "orders": 0, "gmv_percent": 0, "orders_percent": 0}
        }

    # Convert numeric columns
    df["order_gmv"] = pd.to_numeric(df["order_gmv"], errors='coerce')
    usd_rate = CURRENCY_RATES.get(country, 1) if country else 1

    # Total metrics
    total_gmv = df["order_gmv"].sum()
    total_gmv_usd = total_gmv / usd_rate
    total_orders = df["order_number"].nunique()

    # Customer channel (not CX_TLP)
    df_customer = df[df["channel"] != "CX_TLP"]
    customer_gmv = df_customer["order_gmv"].sum()
    customer_gmv_usd = customer_gmv / usd_rate
    customer_orders = df_customer["order_number"].nunique()

    # CX_TLP channel
    df_cx_tlp = df[df["channel"] == "CX_TLP"]
    cx_tlp_gmv = df_cx_tlp["order_gmv"].sum()
    cx_tlp_gmv_usd = cx_tlp_gmv / usd_rate
    cx_tlp_orders = df_cx_tlp["order_number"].nunique()

    # Calculate percentages
    customer_gmv_pct = (customer_gmv_usd / total_gmv_usd * 100) if total_gmv_usd > 0 else 0
    customer_orders_pct = (customer_orders / total_orders * 100) if total_orders > 0 else 0
    cx_tlp_gmv_pct = (cx_tlp_gmv_usd / total_gmv_usd * 100) if total_gmv_usd > 0 else 0
    cx_tlp_orders_pct = (cx_tlp_orders / total_orders * 100) if total_orders > 0 else 0

    return {
        "customer": {
            "gmv_usd": round(customer_gmv_usd, 2),
            "orders": customer_orders,
            "gmv_percent": round(customer_gmv_pct, 1),
            "orders_percent": round(customer_orders_pct, 1)
        },
        "cx_tlp": {
            "gmv_usd": round(cx_tlp_gmv_usd, 2),
            "orders": cx_tlp_orders,
            "gmv_percent": round(cx_tlp_gmv_pct, 1),
            "orders_percent": round(cx_tlp_orders_pct, 1)
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


def generate_json_output(country, metrics_today, metrics_last_week, metrics_mtd, daily_metrics, ma_7d, ma_15d, channel_metrics_today=None, channel_metrics_mtd=None):
    """
    Generate JSON output structure for a country.

    Args:
        country: Country code
        metrics_today: Today's metrics dict
        metrics_last_week: Same day last week metrics dict
        metrics_mtd: Month-to-date metrics dict
        daily_metrics: List of daily metrics dicts
        ma_7d: 7-day moving average dict
        ma_15d: 15-day moving average dict
        channel_metrics_today: Today's channel breakdown dict
        channel_metrics_mtd: MTD channel breakdown dict

    Returns:
        dict ready for JSON serialization
    """
    today = get_today()
    same_day_last_week = get_same_day_last_week()
    mtd_start = get_mtd_start()

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
        "daily_history": daily_metrics,
        "moving_averages": {
            "ma_7d": ma_7d,
            "ma_15d": ma_15d
        }
    }

    # Add channel metrics if available
    if channel_metrics_today:
        output["channel_breakdown_today"] = channel_metrics_today
    if channel_metrics_mtd:
        output["channel_breakdown_mtd"] = channel_metrics_mtd

    return output


def save_json_file(data, country):
    """
    Save data to JSON file.

    Args:
        data: Data dict to save
        country: Country code for filename
    """
    Path(DATA_DIR).mkdir(exist_ok=True)

    filename = f"{DATA_DIR}/{country.lower()}.json"

    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved data to {filename}")
    except Exception as e:
        logger.error(f"Failed to save {filename}: {e}")
        raise


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
        history_start = today - timedelta(days=15)

        for country in COUNTRIES:
            logger.info(f"Processing {country}...")

            # Get current time in country's timezone for same-time-last-week comparison
            country_tz = TIMEZONES.get(country)
            current_time = datetime.now(country_tz)
            current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')

            # Calculate same time last week
            last_week_time = current_time - timedelta(days=7)
            last_week_time_str = last_week_time.strftime('%Y-%m-%d %H:%M:%S')

            logger.info(f"{country} - Current time: {current_time_str} ({country_tz})")
            logger.info(f"{country} - Last week cutoff: {last_week_time_str} ({country_tz})")

            # Query all data needed (last 15 days) - no time filter
            df_all = query_orders(connection, country, history_start, today)

            # Query last week data with time cutoff (up to same time as now)
            df_last_week_cutoff = query_orders(
                connection, country, same_day_last_week, same_day_last_week,
                end_time=last_week_time_str
            )

            if df_all.empty:
                logger.warning(f"No data for {country}, creating empty output...")
                # Create empty structure
                empty_metrics = calculate_metrics(pd.DataFrame(), country)
                data = generate_json_output(
                    country,
                    empty_metrics,
                    empty_metrics,
                    empty_metrics,
                    [],
                    empty_metrics,
                    empty_metrics,
                )
                save_json_file(data, country)
                continue

            # Filter for different time periods (handle mixed ISO8601 formats)
            df_all["date"] = pd.to_datetime(df_all["placement_date"], format='mixed', utc=True).dt.date

            df_today = df_all[df_all["date"] == today]
            df_mtd = df_all[df_all["date"] >= mtd_start]

            # Calculate metrics
            metrics_today = calculate_metrics(df_today, country)
            metrics_last_week = calculate_metrics(df_last_week_cutoff, country)  # Use time-filtered data
            metrics_mtd = calculate_metrics(df_mtd, country)

            # Calculate daily history
            daily_metrics = calculate_daily_metrics(df_all, country)

            # Calculate moving averages
            ma_7d = calculate_moving_average(daily_metrics, 7)
            ma_15d = calculate_moving_average(daily_metrics, 15)

            # Calculate channel metrics
            channel_metrics_today = calculate_channel_metrics(df_today, country)
            channel_metrics_mtd = calculate_channel_metrics(df_mtd, country)

            # Generate and save JSON
            data = generate_json_output(
                country,
                metrics_today,
                metrics_last_week,
                metrics_mtd,
                daily_metrics,
                ma_7d,
                ma_15d,
                channel_metrics_today,
                channel_metrics_mtd,
            )
            save_json_file(data, country)

            logger.info(f"{country} - Today GMV: {metrics_today['total_gmv']}, Orders: {metrics_today['orders']}")
            logger.info(f"{country} - Last week (same time) GMV: {metrics_last_week['total_gmv']}, Orders: {metrics_last_week['orders']}")

        connection.close()
        logger.info("Data extraction completed successfully")

    except Exception as e:
        logger.error(f"Data extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
