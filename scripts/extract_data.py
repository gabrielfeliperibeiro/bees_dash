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


def main():
    """Main execution function."""
    logger.info("Starting data extraction...")

    try:
        # Connect to Databricks
        connection = connect_to_databricks()

        # Test query for today
        today = get_today()
        for country in COUNTRIES:
            df = query_orders(connection, country, today, today)
            logger.info(f"{country}: {len(df)} orders today")

        connection.close()
        logger.info("Data extraction completed successfully")

    except Exception as e:
        logger.error(f"Data extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
