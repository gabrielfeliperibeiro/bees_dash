"""Configuration for Databricks connection and queries."""
import os
from datetime import datetime, timedelta

# Databricks connection
DATABRICKS_SERVER_HOSTNAME = "adb-1825183661408911.11.azuredatabricks.net"
DATABRICKS_HTTP_PATH = "sql/protocolv1/o/1825183661408911/0523-172047-4vu5f6v7"
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")

# Data settings
COUNTRIES = ["PH", "VN"]
HISTORY_DAYS = 60
MOVING_AVERAGE_WINDOWS = [7, 30]

# File paths
DATA_DIR = "data"
LOGS_DIR = "logs"

def get_today():
    """Get today's date."""
    return datetime.now().date()

def get_same_day_last_week():
    """Get date for same day last week."""
    return get_today() - timedelta(days=7)

def get_mtd_start():
    """Get first day of current month."""
    today = datetime.now()
    return datetime(today.year, today.month, 1).date()
