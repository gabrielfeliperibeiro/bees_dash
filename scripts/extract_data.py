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
    DATA_DIR,
    LOGS_DIR,
    get_today,
    get_same_day_last_week,
    get_mtd_start,
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


def query_orders(connection, country, start_date, end_date):
    """
    Query orders from Databricks for a specific country and date range.

    Args:
        connection: Databricks connection
        country: Country code (PH or VN)
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        pandas DataFrame with order data
    """
    query = f"""
    SELECT
        country,
        placement_date,
        order_number,
        order_gmv,
        order_gmv_usd,
        account_id,
        vendor_account_id,
        order_status
    FROM wh_am.sandbox.orders_live_tracking
    WHERE country = '{country}'
    AND TO_DATE(DATE_TRUNC('DAY', placement_date)) >= '{start_date}'
    AND TO_DATE(DATE_TRUNC('DAY', placement_date)) <= '{end_date}'
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


def calculate_metrics(df):
    """
    Calculate sales metrics from order data.

    Args:
        df: pandas DataFrame with order data

    Returns:
        dict with calculated metrics
    """
    if df.empty:
        return {
            "total_gmv": 0,
            "orders": 0,
            "unique_buyers": 0,
            "unique_vendors": 0,
            "aov": 0,
            "frequency": 0,
            "gmv_per_poc": 0,
        }

    total_gmv = df["order_gmv"].sum()
    orders = df["order_number"].nunique()
    unique_buyers = df["account_id"].nunique()
    unique_vendors = df["vendor_account_id"].nunique()

    # Calculate derived metrics
    aov = total_gmv / orders if orders > 0 else 0
    frequency = orders / unique_buyers if unique_buyers > 0 else 0
    gmv_per_poc = total_gmv / unique_vendors if unique_vendors > 0 else 0

    return {
        "total_gmv": round(total_gmv, 2),
        "orders": orders,
        "unique_buyers": unique_buyers,
        "unique_vendors": unique_vendors,
        "aov": round(aov, 2),
        "frequency": round(frequency, 2),
        "gmv_per_poc": round(gmv_per_poc, 2),
    }


def calculate_daily_metrics(df):
    """
    Calculate metrics grouped by day.

    Args:
        df: pandas DataFrame with order data

    Returns:
        list of dicts with daily metrics
    """
    if df.empty:
        return []

    # Convert placement_date to date (handle ISO8601 format with UTC)
    df["date"] = pd.to_datetime(df["placement_date"], utc=True).dt.date

    daily_metrics = []
    for date, group in df.groupby("date"):
        metrics = calculate_metrics(group)
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

    # Calculate averages
    avg_gmv = sum(d["total_gmv"] for d in recent_data) / window
    avg_orders = sum(d["orders"] for d in recent_data) / window
    avg_aov = sum(d["aov"] for d in recent_data) / window
    avg_buyers = sum(d["unique_buyers"] for d in recent_data) / window
    avg_frequency = sum(d["frequency"] for d in recent_data) / window
    avg_gmv_per_poc = sum(d["gmv_per_poc"] for d in recent_data) / window

    return {
        "gmv": round(avg_gmv, 2),
        "orders": round(avg_orders, 2),
        "aov": round(avg_aov, 2),
        "unique_buyers": round(avg_buyers, 2),
        "frequency": round(avg_frequency, 2),
        "gmv_per_poc": round(avg_gmv_per_poc, 2),
    }


def generate_json_output(country, metrics_today, metrics_last_week, metrics_mtd, daily_metrics, ma_7d, ma_30d):
    """
    Generate JSON output structure for a country.

    Args:
        country: Country code
        metrics_today: Today's metrics dict
        metrics_last_week: Same day last week metrics dict
        metrics_mtd: Month-to-date metrics dict
        daily_metrics: List of daily metrics dicts
        ma_7d: 7-day moving average dict
        ma_30d: 30-day moving average dict

    Returns:
        dict ready for JSON serialization
    """
    today = get_today()
    same_day_last_week = get_same_day_last_week()
    mtd_start = get_mtd_start()

    return {
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
            "ma_30d": ma_30d
        }
    }


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
        history_start = today - timedelta(days=60)

        for country in COUNTRIES:
            logger.info(f"Processing {country}...")

            # Query all data needed (last 60 days)
            df_all = query_orders(connection, country, history_start, today)

            if df_all.empty:
                logger.warning(f"No data for {country}, creating empty output...")
                # Create empty structure
                empty_metrics = calculate_metrics(pd.DataFrame())
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

            # Filter for different time periods (handle ISO8601 format with UTC)
            df_all["date"] = pd.to_datetime(df_all["placement_date"], utc=True).dt.date

            df_today = df_all[df_all["date"] == today]
            df_last_week = df_all[df_all["date"] == same_day_last_week]
            df_mtd = df_all[df_all["date"] >= mtd_start]

            # Calculate metrics
            metrics_today = calculate_metrics(df_today)
            metrics_last_week = calculate_metrics(df_last_week)
            metrics_mtd = calculate_metrics(df_mtd)

            # Calculate daily history
            daily_metrics = calculate_daily_metrics(df_all)

            # Calculate moving averages
            ma_7d = calculate_moving_average(daily_metrics, 7)
            ma_30d = calculate_moving_average(daily_metrics, 30)

            # Generate and save JSON
            data = generate_json_output(
                country,
                metrics_today,
                metrics_last_week,
                metrics_mtd,
                daily_metrics,
                ma_7d,
                ma_30d,
            )
            save_json_file(data, country)

            logger.info(f"{country} - Today GMV: {metrics_today['total_gmv']}, Orders: {metrics_today['orders']}")

        connection.close()
        logger.info("Data extraction completed successfully")

    except Exception as e:
        logger.error(f"Data extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
