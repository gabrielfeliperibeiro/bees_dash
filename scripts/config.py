"""Configuration for Databricks connection and queries."""
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Databricks connection
DATABRICKS_SERVER_HOSTNAME = "adb-1825183661408911.11.azuredatabricks.net"
DATABRICKS_HTTP_PATH = "sql/protocolv1/o/1825183661408911/0523-172047-4vu5f6v7"
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")

# Data settings
COUNTRIES = ["PH", "VN"]
HISTORY_DAYS = 60
MOVING_AVERAGE_WINDOWS = [7, 30]

# Currency conversion rates to USD
CURRENCY_RATES = {
    "PH": 56.017,  # PHP to USD
    "VN": 26416,   # VND to USD
}

# Timezone settings
TIMEZONES = {
    "PH": ZoneInfo("Asia/Manila"),      # UTC+8
    "VN": ZoneInfo("Asia/Ho_Chi_Minh"), # UTC+7
    "HK": ZoneInfo("Asia/Hong_Kong"),   # UTC+8 (for display)
}

# File paths (relative to repository root)
DATA_DIR = "../data"
LOGS_DIR = "../logs"

def get_today():
    """Get today's date in Hong Kong timezone."""
    hk_now = datetime.now(TIMEZONES["HK"])
    return hk_now.date()

def get_same_day_last_week():
    """Get date for same day last week in Hong Kong timezone."""
    return get_today() - timedelta(days=7)

def get_mtd_start():
    """Get first day of current month in Hong Kong timezone."""
    hk_now = datetime.now(TIMEZONES["HK"])
    return datetime(hk_now.year, hk_now.month, 1, tzinfo=TIMEZONES["HK"]).date()

def get_last_month_mtd_range():
    """
    Get same MTD date range from last month.
    Example: If today is Jan 27, returns (Dec 1, Dec 27)
    """
    hk_now = datetime.now(TIMEZONES["HK"])
    today = hk_now.date()
    day_of_month = today.day

    # Get first day of last month
    if hk_now.month == 1:
        last_month_start = datetime(hk_now.year - 1, 12, 1, tzinfo=TIMEZONES["HK"]).date()
    else:
        last_month_start = datetime(hk_now.year, hk_now.month - 1, 1, tzinfo=TIMEZONES["HK"]).date()

    # Get same day of last month (or last day if day doesn't exist)
    try:
        if hk_now.month == 1:
            last_month_end = datetime(hk_now.year - 1, 12, day_of_month, tzinfo=TIMEZONES["HK"]).date()
        else:
            last_month_end = datetime(hk_now.year, hk_now.month - 1, day_of_month, tzinfo=TIMEZONES["HK"]).date()
    except ValueError:
        # Day doesn't exist in last month (e.g., Jan 31 -> Feb 28/29)
        # Use last day of last month
        if hk_now.month == 1:
            last_month_end = datetime(hk_now.year - 1, 12, 31, tzinfo=TIMEZONES["HK"]).date()
        else:
            # Get last day of previous month
            first_of_this_month = datetime(hk_now.year, hk_now.month, 1, tzinfo=TIMEZONES["HK"])
            last_month_end = (first_of_this_month - timedelta(days=1)).date()

    return last_month_start, last_month_end

def get_hk_time():
    """Get current time in Hong Kong timezone for display."""
    return datetime.now(TIMEZONES["HK"])

def get_hk_now_utc():
    """Get current Hong Kong time as UTC for database queries."""
    hk_now = datetime.now(TIMEZONES["HK"])
    # Convert to UTC for database queries
    return hk_now.astimezone(ZoneInfo("UTC"))
