# Sales Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a real-time sales dashboard that displays PH and VN metrics side-by-side, updated every 5 minutes via GitHub Actions pulling from Databricks.

**Architecture:** GitHub Actions runs Python script every 5 minutes to query Databricks, calculate metrics, and commit JSON files. Static frontend hosted on GitHub Pages fetches JSON and displays side-by-side dashboards with charts.

**Tech Stack:** Python 3.11, databricks-sql-connector, pandas, Chart.js, Vanilla JS, GitHub Actions, GitHub Pages

---

## Task 1: Project Structure & Dependencies

**Files:**
- Create: `scripts/requirements.txt`
- Create: `.gitignore`
- Create: `data/.gitkeep`
- Create: `logs/.gitkeep`
- Create: `README.md`

**Step 1: Create Python dependencies file**

Create `scripts/requirements.txt`:
```
databricks-sql-connector==3.0.2
pandas==2.1.4
python-dateutil==2.8.2
```

**Step 2: Create .gitignore**

Create `.gitignore`:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment variables
.env
.env.local

# Logs
logs/*.log

# OS
.DS_Store
Thumbs.db
```

**Step 3: Create placeholder files for directories**

```bash
touch data/.gitkeep
touch logs/.gitkeep
```

**Step 4: Create README**

Create `README.md`:
```markdown
# Sales Dashboard - Real-Time

Real-time sales dashboard for PH and VN markets with automated data updates from Databricks.

## Features

- Side-by-side view of PH and VN metrics
- Key metrics: GMV, Orders, AOV, Buyers, Frequency, GMV/POCs
- Comparisons: Today vs Last Week, MTD
- Moving averages: 7-day and 30-day
- Auto-refresh every 5 minutes

## Setup

### Prerequisites

- Python 3.11+
- Access to Databricks with provided credentials
- GitHub repository with Actions enabled

### Installation

1. Install Python dependencies:
   ```bash
   pip install -r scripts/requirements.txt
   ```

2. Configure GitHub Secrets:
   - `DATABRICKS_TOKEN`: Your Databricks access token

3. Run historical backfill (first time only):
   ```bash
   python scripts/backfill_historical.py
   ```

4. GitHub Actions will automatically update data every 5 minutes

## Development

- `scripts/extract_data.py`: Main data extraction script
- `scripts/backfill_historical.py`: One-time historical data loader
- `index.html`: Dashboard frontend
- `app.js`: Frontend logic
- `styles.css`: Dashboard styling

## Deployment

GitHub Pages automatically deploys from the `main` branch.

Dashboard URL: https://[username].github.io/bees_dash/
```

**Step 5: Commit project structure**

```bash
git add .gitignore scripts/requirements.txt data/.gitkeep logs/.gitkeep README.md
git commit -m "chore: initialize project structure and dependencies"
```

---

## Task 2: Data Extraction Script - Connection & Query

**Files:**
- Create: `scripts/extract_data.py`
- Create: `scripts/config.py`

**Step 1: Create configuration module**

Create `scripts/config.py`:
```python
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
```

**Step 2: Create data extraction script with connection**

Create `scripts/extract_data.py`:
```python
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
```

**Step 3: Test connection script**

Run: `cd scripts && python extract_data.py`
Expected: Should connect to Databricks and log order counts for PH and VN

**Step 4: Commit data extraction foundation**

```bash
git add scripts/config.py scripts/extract_data.py
git commit -m "feat: add databricks connection and query logic"
```

---

## Task 3: Metrics Calculation Functions

**Files:**
- Modify: `scripts/extract_data.py`

**Step 1: Add metrics calculation functions**

Add to `scripts/extract_data.py` after the `query_orders` function:

```python
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

    # Convert placement_date to date
    df["date"] = pd.to_datetime(df["placement_date"]).dt.date

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
```

**Step 2: Update main function to calculate metrics**

Replace the `main()` function in `scripts/extract_data.py`:

```python
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
                logger.warning(f"No data for {country}, skipping...")
                continue

            # Filter for different time periods
            df_all["date"] = pd.to_datetime(df_all["placement_date"]).dt.date

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

            logger.info(f"{country} - Today GMV: {metrics_today['total_gmv']}, Orders: {metrics_today['orders']}")

        connection.close()
        logger.info("Data extraction completed successfully")

    except Exception as e:
        logger.error(f"Data extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 3: Test metrics calculation**

Run: `cd scripts && python extract_data.py`
Expected: Should log calculated metrics for today including GMV and orders

**Step 4: Commit metrics calculation**

```bash
git add scripts/extract_data.py
git commit -m "feat: add metrics calculation functions"
```

---

## Task 4: JSON Generation and File Writing

**Files:**
- Modify: `scripts/extract_data.py`

**Step 1: Add JSON generation function**

Add to `scripts/extract_data.py` after the moving average function:

```python
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
```

**Step 2: Update main function to generate and save JSON**

Replace the `main()` function in `scripts/extract_data.py`:

```python
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

            # Filter for different time periods
            df_all["date"] = pd.to_datetime(df_all["placement_date"]).dt.date

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
```

**Step 3: Test JSON generation**

Run: `cd scripts && python extract_data.py`
Expected: Should create `data/ph.json` and `data/vn.json` files

**Step 4: Verify JSON structure**

Run: `cat data/ph.json | head -20`
Expected: Should show properly formatted JSON with today, same_day_last_week, mtd sections

**Step 5: Commit JSON generation**

```bash
git add scripts/extract_data.py data/ph.json data/vn.json
git commit -m "feat: add json generation and file writing"
```

---

## Task 5: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/update-dashboard.yml`

**Step 1: Create GitHub Actions workflow**

Create `.github/workflows/update-dashboard.yml`:

```yaml
name: Update Dashboard Data

on:
  schedule:
    # Run every 5 minutes
    - cron: '*/5 * * * *'

  # Allow manual trigger
  workflow_dispatch:

  # Run on push to main
  push:
    branches:
      - main

jobs:
  update-data:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r scripts/requirements.txt

      - name: Extract data from Databricks
        env:
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
        run: |
          cd scripts
          python extract_data.py

      - name: Configure Git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      - name: Commit and push data
        run: |
          git add data/*.json

          # Only commit if there are changes
          if git diff --staged --quiet; then
            echo "No changes to commit"
          else
            git commit -m "data: update dashboard data - $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
            git push
          fi
```

**Step 2: Create workflow for historical backfill**

Create `.github/workflows/backfill.yml`:

```yaml
name: Backfill Historical Data

on:
  # Manual trigger only
  workflow_dispatch:

jobs:
  backfill:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r scripts/requirements.txt

      - name: Run backfill
        env:
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
        run: |
          cd scripts
          python backfill_historical.py

      - name: Configure Git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      - name: Commit and push data
        run: |
          git add data/*.json
          git commit -m "data: backfill historical data - $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
          git push
```

**Step 3: Create backfill script placeholder**

Create `scripts/backfill_historical.py`:

```python
"""One-time script to backfill 60 days of historical data."""
import sys
import logging
from datetime import datetime

# Reuse extract_data logic
from extract_data import main, logger

if __name__ == "__main__":
    logger.info("Running historical backfill...")
    logger.info("This will fetch 60 days of data from Databricks")

    # The extract_data main function already handles 60 days
    main()

    logger.info("Historical backfill completed")
```

**Step 4: Commit GitHub Actions workflows**

```bash
git add .github/workflows/update-dashboard.yml .github/workflows/backfill.yml scripts/backfill_historical.py
git commit -m "feat: add github actions workflows for data updates"
```

---

## Task 6: Frontend HTML Structure

**Files:**
- Create: `index.html`

**Step 1: Create HTML structure**

Create `index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sales Dashboard - Real-Time</title>
    <link rel="stylesheet" href="styles.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="header-content">
                <h1 class="logo">Sales Dashboard</h1>
                <div class="header-info">
                    <div class="status-indicator" id="statusIndicator">
                        <span class="status-dot"></span>
                        <span class="status-text">Live</span>
                    </div>
                    <div class="last-updated" id="lastUpdated">
                        Loading...
                    </div>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <main class="main-content">
            <!-- Philippines Dashboard -->
            <section class="country-dashboard" id="ph-dashboard">
                <h2 class="country-title">
                    <span class="country-flag">🇵🇭</span>
                    Philippines
                </h2>

                <!-- Hero Metrics -->
                <div class="metrics-grid hero-metrics">
                    <div class="metric-card">
                        <div class="metric-label">Total GMV</div>
                        <div class="metric-value" id="ph-gmv">-</div>
                        <div class="metric-change" id="ph-gmv-change">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Orders</div>
                        <div class="metric-value" id="ph-orders">-</div>
                        <div class="metric-change" id="ph-orders-change">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">AOV</div>
                        <div class="metric-value" id="ph-aov">-</div>
                        <div class="metric-change" id="ph-aov-change">-</div>
                    </div>
                </div>

                <!-- Secondary Metrics -->
                <div class="metrics-grid secondary-metrics">
                    <div class="metric-card">
                        <div class="metric-label">Buyers</div>
                        <div class="metric-value" id="ph-buyers">-</div>
                        <div class="metric-change" id="ph-buyers-change">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Frequency</div>
                        <div class="metric-value" id="ph-frequency">-</div>
                        <div class="metric-change" id="ph-frequency-change">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">GMV/POCs</div>
                        <div class="metric-value" id="ph-gmv-poc">-</div>
                        <div class="metric-change" id="ph-gmv-poc-change">-</div>
                    </div>
                </div>

                <!-- Comparison Table -->
                <div class="comparison-section">
                    <h3 class="section-title">Performance Comparison</h3>
                    <table class="comparison-table" id="ph-comparison-table">
                        <thead>
                            <tr>
                                <th>Metric</th>
                                <th>Today</th>
                                <th>Last Week</th>
                                <th>Change</th>
                                <th>MTD</th>
                            </tr>
                        </thead>
                        <tbody>
                            <!-- Populated by JS -->
                        </tbody>
                    </table>
                </div>

                <!-- Charts -->
                <div class="charts-section">
                    <div class="chart-container">
                        <h3 class="section-title">GMV Trend (30 Days)</h3>
                        <canvas id="ph-gmv-chart"></canvas>
                    </div>
                    <div class="chart-container">
                        <h3 class="section-title">Orders Trend (30 Days)</h3>
                        <canvas id="ph-orders-chart"></canvas>
                    </div>
                </div>
            </section>

            <!-- Vietnam Dashboard -->
            <section class="country-dashboard" id="vn-dashboard">
                <h2 class="country-title">
                    <span class="country-flag">🇻🇳</span>
                    Vietnam
                </h2>

                <!-- Hero Metrics -->
                <div class="metrics-grid hero-metrics">
                    <div class="metric-card">
                        <div class="metric-label">Total GMV</div>
                        <div class="metric-value" id="vn-gmv">-</div>
                        <div class="metric-change" id="vn-gmv-change">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Orders</div>
                        <div class="metric-value" id="vn-orders">-</div>
                        <div class="metric-change" id="vn-orders-change">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">AOV</div>
                        <div class="metric-value" id="vn-aov">-</div>
                        <div class="metric-change" id="vn-aov-change">-</div>
                    </div>
                </div>

                <!-- Secondary Metrics -->
                <div class="metrics-grid secondary-metrics">
                    <div class="metric-card">
                        <div class="metric-label">Buyers</div>
                        <div class="metric-value" id="vn-buyers">-</div>
                        <div class="metric-change" id="vn-buyers-change">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Frequency</div>
                        <div class="metric-value" id="vn-frequency">-</div>
                        <div class="metric-change" id="vn-frequency-change">-</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">GMV/POCs</div>
                        <div class="metric-value" id="vn-gmv-poc">-</div>
                        <div class="metric-change" id="vn-gmv-poc-change">-</div>
                    </div>
                </div>

                <!-- Comparison Table -->
                <div class="comparison-section">
                    <h3 class="section-title">Performance Comparison</h3>
                    <table class="comparison-table" id="vn-comparison-table">
                        <thead>
                            <tr>
                                <th>Metric</th>
                                <th>Today</th>
                                <th>Last Week</th>
                                <th>Change</th>
                                <th>MTD</th>
                            </tr>
                        </thead>
                        <tbody>
                            <!-- Populated by JS -->
                        </tbody>
                    </table>
                </div>

                <!-- Charts -->
                <div class="charts-section">
                    <div class="chart-container">
                        <h3 class="section-title">GMV Trend (30 Days)</h3>
                        <canvas id="vn-gmv-chart"></canvas>
                    </div>
                    <div class="chart-container">
                        <h3 class="section-title">Orders Trend (30 Days)</h3>
                        <canvas id="vn-orders-chart"></canvas>
                    </div>
                </div>
            </section>
        </main>
    </div>

    <script src="app.js"></script>
</body>
</html>
```

**Step 2: Commit HTML structure**

```bash
git add index.html
git commit -m "feat: add dashboard html structure"
```

---

## Task 7: Frontend CSS Styling

**Files:**
- Create: `styles.css`

**Step 1: Create CSS with dark theme styling**

Create `styles.css`:

```css
/* Reset and Base Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    /* Colors */
    --bg-primary: #0f0f0f;
    --bg-secondary: #1a1a1a;
    --bg-card: #252525;
    --text-primary: #ffffff;
    --text-secondary: #a0a0a0;
    --border-color: #333333;

    /* Accent colors */
    --purple: #8b5cf6;
    --blue: #3b82f6;
    --green: #10b981;
    --red: #ef4444;
    --yellow: #f59e0b;

    /* Spacing */
    --spacing-xs: 0.5rem;
    --spacing-sm: 1rem;
    --spacing-md: 1.5rem;
    --spacing-lg: 2rem;
    --spacing-xl: 3rem;

    /* Border radius */
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
    color: var(--text-primary);
    min-height: 100vh;
    line-height: 1.6;
}

.container {
    max-width: 1800px;
    margin: 0 auto;
    padding: var(--spacing-md);
}

/* Header */
.header {
    margin-bottom: var(--spacing-lg);
}

.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md);
    background: var(--bg-card);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-color);
}

.logo {
    font-size: 1.75rem;
    font-weight: 700;
    background: linear-gradient(135deg, var(--purple), var(--blue));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.header-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.status-indicator {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-xs) var(--spacing-sm);
    background: rgba(16, 185, 129, 0.1);
    border-radius: 20px;
}

.status-dot {
    width: 8px;
    height: 8px;
    background: var(--green);
    border-radius: 50%;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.status-text {
    font-size: 0.875rem;
    color: var(--green);
    font-weight: 600;
}

.last-updated {
    font-size: 0.875rem;
    color: var(--text-secondary);
}

/* Main Content */
.main-content {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-lg);
}

.country-dashboard {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
}

.country-title {
    font-size: 1.5rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-sm);
}

.country-flag {
    font-size: 2rem;
}

/* Metrics Grid */
.metrics-grid {
    display: grid;
    gap: var(--spacing-sm);
}

.hero-metrics {
    grid-template-columns: repeat(3, 1fr);
}

.secondary-metrics {
    grid-template-columns: repeat(3, 1fr);
}

.metric-card {
    background: var(--bg-card);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-color);
    transition: transform 0.2s, border-color 0.2s;
}

.metric-card:hover {
    transform: translateY(-2px);
    border-color: var(--purple);
}

.metric-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-bottom: var(--spacing-xs);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.metric-value {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: var(--spacing-xs);
    font-variant-numeric: tabular-nums;
}

.hero-metrics .metric-value {
    font-size: 2.5rem;
}

.metric-change {
    font-size: 0.875rem;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 6px;
    display: inline-block;
}

.metric-change.positive {
    color: var(--green);
    background: rgba(16, 185, 129, 0.1);
}

.metric-change.negative {
    color: var(--red);
    background: rgba(239, 68, 68, 0.1);
}

.metric-change.neutral {
    color: var(--text-secondary);
    background: rgba(160, 160, 160, 0.1);
}

/* Comparison Section */
.comparison-section {
    background: var(--bg-card);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-color);
}

.section-title {
    font-size: 1.125rem;
    font-weight: 600;
    margin-bottom: var(--spacing-md);
}

.comparison-table {
    width: 100%;
    border-collapse: collapse;
}

.comparison-table th {
    text-align: left;
    padding: var(--spacing-sm);
    font-size: 0.875rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--border-color);
}

.comparison-table td {
    padding: var(--spacing-sm);
    font-variant-numeric: tabular-nums;
    border-bottom: 1px solid var(--border-color);
}

.comparison-table tbody tr:last-child td {
    border-bottom: none;
}

.comparison-table .change-cell {
    font-weight: 600;
}

.comparison-table .change-cell.positive {
    color: var(--green);
}

.comparison-table .change-cell.negative {
    color: var(--red);
}

/* Charts Section */
.charts-section {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-md);
}

.chart-container {
    background: var(--bg-card);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-color);
}

.chart-container canvas {
    max-height: 250px;
}

/* Responsive Design */
@media (max-width: 1400px) {
    .main-content {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 768px) {
    .header-content {
        flex-direction: column;
        gap: var(--spacing-sm);
    }

    .hero-metrics,
    .secondary-metrics {
        grid-template-columns: 1fr;
    }

    .charts-section {
        grid-template-columns: 1fr;
    }

    .metric-value {
        font-size: 1.5rem;
    }

    .hero-metrics .metric-value {
        font-size: 2rem;
    }
}
```

**Step 2: Commit CSS styling**

```bash
git add styles.css
git commit -m "feat: add dashboard css styling with dark theme"
```

---

## Task 8: Frontend JavaScript - Data Loading

**Files:**
- Create: `app.js`

**Step 1: Create JavaScript with data loading and retry logic**

Create `app.js`:

```javascript
// Configuration
const CONFIG = {
    dataFiles: {
        ph: 'data/ph.json',
        vn: 'data/vn.json'
    },
    refreshInterval: 5 * 60 * 1000, // 5 minutes
    retryAttempts: 3,
    retryDelays: [0, 10000, 20000], // 0s, 10s, 20s (total 30s window)
    staleThresholds: {
        warning: 10 * 60 * 1000, // 10 minutes
        error: 30 * 60 * 1000 // 30 minutes
    }
};

// Global state
let dashboardData = {
    ph: null,
    vn: null
};

let charts = {
    ph: { gmv: null, orders: null },
    vn: { gmv: null, orders: null }
};

/**
 * Fetch data with retry logic (3 attempts within 30 seconds)
 */
async function fetchWithRetry(url, attemptNumber = 0) {
    try {
        if (attemptNumber > 0) {
            await new Promise(resolve => setTimeout(resolve, CONFIG.retryDelays[attemptNumber]));
        }

        console.log(`Fetching ${url} (attempt ${attemptNumber + 1}/${CONFIG.retryAttempts})`);

        const response = await fetch(url + '?t=' + Date.now()); // Cache busting

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log(`Successfully fetched ${url}`);
        return data;

    } catch (error) {
        console.error(`Fetch attempt ${attemptNumber + 1} failed for ${url}:`, error);

        if (attemptNumber < CONFIG.retryAttempts - 1) {
            return fetchWithRetry(url, attemptNumber + 1);
        } else {
            throw new Error(`Failed to fetch ${url} after ${CONFIG.retryAttempts} attempts`);
        }
    }
}

/**
 * Load data for both countries
 */
async function loadDashboardData() {
    try {
        console.log('Loading dashboard data...');

        // Fetch both countries in parallel
        const [phData, vnData] = await Promise.all([
            fetchWithRetry(CONFIG.dataFiles.ph),
            fetchWithRetry(CONFIG.dataFiles.vn)
        ]);

        dashboardData.ph = phData;
        dashboardData.vn = vnData;

        console.log('Dashboard data loaded successfully');

        // Update UI
        updateDashboard();
        updateStatusIndicator();

    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        showError('Unable to load dashboard data. Please try again.');
    }
}

/**
 * Update status indicator based on data freshness
 */
function updateStatusIndicator() {
    const statusIndicator = document.getElementById('statusIndicator');
    const lastUpdatedEl = document.getElementById('lastUpdated');

    // Use PH data timestamp (both should be the same)
    const lastUpdated = dashboardData.ph?.last_updated;

    if (!lastUpdated) {
        lastUpdatedEl.textContent = 'No data';
        return;
    }

    const lastUpdateTime = new Date(lastUpdated);
    const now = new Date();
    const timeDiff = now - lastUpdateTime;

    // Update last updated text
    lastUpdatedEl.textContent = `Updated ${formatTimeAgo(lastUpdateTime)}`;

    // Update status indicator
    const statusDot = statusIndicator.querySelector('.status-dot');
    const statusText = statusIndicator.querySelector('.status-text');

    if (timeDiff < CONFIG.staleThresholds.warning) {
        // Green - Fresh data
        statusIndicator.style.background = 'rgba(16, 185, 129, 0.1)';
        statusDot.style.background = '#10b981';
        statusText.style.color = '#10b981';
        statusText.textContent = 'Live';
    } else if (timeDiff < CONFIG.staleThresholds.error) {
        // Yellow - Slightly stale
        statusIndicator.style.background = 'rgba(245, 158, 11, 0.1)';
        statusDot.style.background = '#f59e0b';
        statusText.style.color = '#f59e0b';
        statusText.textContent = 'Delayed';
    } else {
        // Red - Very stale
        statusIndicator.style.background = 'rgba(239, 68, 68, 0.1)';
        statusDot.style.background = '#ef4444';
        statusText.style.color = '#ef4444';
        statusText.textContent = 'Stale';
    }
}

/**
 * Format time difference in human-readable format
 */
function formatTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 120) return '1 min ago';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} mins ago`;
    if (seconds < 7200) return '1 hour ago';
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;

    return date.toLocaleString();
}

/**
 * Show error message
 */
function showError(message) {
    console.error(message);
    // TODO: Add visual error display
    alert(message);
}

/**
 * Format number with commas
 */
function formatNumber(num, decimals = 0) {
    if (num === null || num === undefined) return '-';
    return num.toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

/**
 * Calculate percentage change
 */
function calculateChange(current, previous) {
    if (!previous || previous === 0) return 0;
    return ((current - previous) / previous) * 100;
}

/**
 * Format percentage change with sign
 */
function formatChangePercent(change) {
    const sign = change > 0 ? '+' : '';
    return `${sign}${change.toFixed(1)}%`;
}

/**
 * Get change class (positive/negative/neutral)
 */
function getChangeClass(change) {
    if (change > 0) return 'positive';
    if (change < 0) return 'negative';
    return 'neutral';
}

// Placeholder for update functions (to be implemented in next task)
function updateDashboard() {
    console.log('Updating dashboard...');
    updateCountryDashboard('ph', dashboardData.ph);
    updateCountryDashboard('vn', dashboardData.vn);
}

function updateCountryDashboard(country, data) {
    console.log(`Updating ${country} dashboard...`, data);
    // TODO: Implement in next task
}

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard initializing...');
    loadDashboardData();

    // Set up auto-refresh
    setInterval(() => {
        console.log('Auto-refreshing dashboard...');
        loadDashboardData();
    }, CONFIG.refreshInterval);
});
```

**Step 2: Test data loading**

Run: `python -m http.server 8000` (in project root)
Open: `http://localhost:8000/`
Expected: Console should show data loading attempts and success

**Step 3: Commit JavaScript data loading**

```bash
git add app.js
git commit -m "feat: add javascript data loading with retry logic"
```

---

## Task 9: Frontend JavaScript - Dashboard Rendering

**Files:**
- Modify: `app.js`

**Step 1: Add dashboard rendering functions**

Replace the placeholder functions in `app.js` with:

```javascript
/**
 * Update dashboard for a country
 */
function updateCountryDashboard(country, data) {
    if (!data) {
        console.warn(`No data for ${country}`);
        return;
    }

    updateMetricCards(country, data);
    updateComparisonTable(country, data);
    updateCharts(country, data);
}

/**
 * Update metric cards
 */
function updateMetricCards(country, data) {
    const today = data.today;
    const lastWeek = data.same_day_last_week;

    // Helper to update a metric card
    const updateCard = (metric, value, decimals = 0) => {
        const valueEl = document.getElementById(`${country}-${metric}`);
        const changeEl = document.getElementById(`${country}-${metric}-change`);

        if (!valueEl || !changeEl) return;

        // Update value
        valueEl.textContent = formatNumber(today[value], decimals);

        // Calculate and update change
        const change = calculateChange(today[value], lastWeek[value]);
        changeEl.textContent = formatChangePercent(change);
        changeEl.className = 'metric-change ' + getChangeClass(change);
    };

    // Update hero metrics
    updateCard('gmv', 'total_gmv', 2);
    updateCard('orders', 'orders', 0);
    updateCard('aov', 'aov', 2);

    // Update secondary metrics
    updateCard('buyers', 'unique_buyers', 0);
    updateCard('frequency', 'frequency', 2);
    updateCard('gmv-poc', 'gmv_per_poc', 2);
}

/**
 * Update comparison table
 */
function updateComparisonTable(country, data) {
    const tableId = `${country}-comparison-table`;
    const tbody = document.querySelector(`#${tableId} tbody`);

    if (!tbody) return;

    const today = data.today;
    const lastWeek = data.same_day_last_week;
    const mtd = data.mtd;

    const metrics = [
        { label: 'GMV', key: 'total_gmv', decimals: 2 },
        { label: 'Orders', key: 'orders', decimals: 0 },
        { label: 'Buyers', key: 'unique_buyers', decimals: 0 },
        { label: 'AOV', key: 'aov', decimals: 2 },
        { label: 'Frequency', key: 'frequency', decimals: 2 },
        { label: 'GMV/POCs', key: 'gmv_per_poc', decimals: 2 }
    ];

    tbody.innerHTML = metrics.map(metric => {
        const todayValue = today[metric.key];
        const lastWeekValue = lastWeek[metric.key];
        const mtdValue = mtd[metric.key];
        const change = calculateChange(todayValue, lastWeekValue);

        return `
            <tr>
                <td><strong>${metric.label}</strong></td>
                <td>${formatNumber(todayValue, metric.decimals)}</td>
                <td>${formatNumber(lastWeekValue, metric.decimals)}</td>
                <td class="change-cell ${getChangeClass(change)}">${formatChangePercent(change)}</td>
                <td>${formatNumber(mtdValue, metric.decimals)}</td>
            </tr>
        `;
    }).join('');
}

/**
 * Update charts
 */
function updateCharts(country, data) {
    const dailyHistory = data.daily_history || [];
    const movingAverages = data.moving_averages || {};

    // Prepare data (last 30 days)
    const last30Days = dailyHistory.slice(-30);
    const dates = last30Days.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });

    // GMV data
    const gmvData = last30Days.map(d => d.total_gmv);
    const gmvMA7 = new Array(last30Days.length).fill(movingAverages.ma_7d?.gmv || 0);
    const gmvMA30 = new Array(last30Days.length).fill(movingAverages.ma_30d?.gmv || 0);

    // Orders data
    const ordersData = last30Days.map(d => d.orders);
    const ordersMA7 = new Array(last30Days.length).fill(movingAverages.ma_7d?.orders || 0);
    const ordersMA30 = new Array(last30Days.length).fill(movingAverages.ma_30d?.orders || 0);

    // Create or update GMV chart
    updateChart(
        `${country}-gmv-chart`,
        charts[country].gmv,
        dates,
        gmvData,
        gmvMA7,
        gmvMA30,
        'GMV'
    );

    // Create or update Orders chart
    updateChart(
        `${country}-orders-chart`,
        charts[country].orders,
        dates,
        ordersData,
        ordersMA7,
        ordersMA30,
        'Orders'
    );
}

/**
 * Create or update a chart
 */
function updateChart(canvasId, existingChart, labels, data, ma7, ma30, label) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const chartData = {
        labels: labels,
        datasets: [
            {
                label: label,
                data: data,
                borderColor: '#8b5cf6',
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 4
            },
            {
                label: '7-day MA',
                data: ma7,
                borderColor: '#3b82f6',
                borderWidth: 2,
                borderDash: [5, 5],
                tension: 0.4,
                fill: false,
                pointRadius: 0
            },
            {
                label: '30-day MA',
                data: ma30,
                borderColor: '#10b981',
                borderWidth: 2,
                borderDash: [5, 5],
                tension: 0.4,
                fill: false,
                pointRadius: 0
            }
        ]
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                display: true,
                position: 'top',
                labels: {
                    color: '#a0a0a0',
                    font: { size: 11 },
                    usePointStyle: true
                }
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: '#252525',
                titleColor: '#ffffff',
                bodyColor: '#a0a0a0',
                borderColor: '#333333',
                borderWidth: 1
            }
        },
        scales: {
            x: {
                grid: {
                    color: '#333333',
                    drawBorder: false
                },
                ticks: {
                    color: '#a0a0a0',
                    font: { size: 10 }
                }
            },
            y: {
                grid: {
                    color: '#333333',
                    drawBorder: false
                },
                ticks: {
                    color: '#a0a0a0',
                    font: { size: 10 },
                    callback: function(value) {
                        return formatNumber(value, 0);
                    }
                }
            }
        },
        interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
        }
    };

    // Destroy existing chart if it exists
    if (existingChart) {
        existingChart.destroy();
    }

    // Create new chart
    const country = canvasId.split('-')[0];
    const chartType = canvasId.includes('gmv') ? 'gmv' : 'orders';
    charts[country][chartType] = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: chartOptions
    });
}
```

**Step 2: Test dashboard rendering**

Run: `python -m http.server 8000`
Open: `http://localhost:8000/`
Expected: Dashboard should display metrics, tables, and charts

**Step 3: Commit dashboard rendering**

```bash
git add app.js
git commit -m "feat: add dashboard rendering with metrics, tables, and charts"
```

---

## Task 10: GitHub Pages Configuration

**Files:**
- Create: `.github/workflows/pages.yml`
- Modify: `README.md`

**Step 1: Create GitHub Pages deployment workflow**

Create `.github/workflows/pages.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Pages
        uses: actions/configure-pages@v4

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '.'

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

**Step 2: Update README with deployment instructions**

Update the "Deployment" section in `README.md`:

```markdown
## Deployment

### GitHub Pages Setup

1. Go to your repository Settings > Pages
2. Under "Build and deployment":
   - Source: GitHub Actions
3. The site will be available at: `https://[username].github.io/bees_dash/`

### GitHub Secrets Setup

Add the following secret to your repository (Settings > Secrets and variables > Actions):

- **DATABRICKS_TOKEN**: Your Databricks access token
  - Value: `dapi6b9bd2e011c8b6ea6282d16aa9082efd-3`

### First-Time Setup

1. Run the backfill workflow manually:
   - Go to Actions > Backfill Historical Data > Run workflow
   - This will load 60 days of historical data

2. The update workflow will run automatically every 5 minutes after that

### Manual Updates

You can manually trigger data updates:
- Go to Actions > Update Dashboard Data > Run workflow
```

**Step 3: Commit GitHub Pages configuration**

```bash
git add .github/workflows/pages.yml README.md
git commit -m "feat: add github pages deployment configuration"
```

---

## Task 11: Testing and Validation

**Files:**
- Create: `docs/testing-checklist.md`

**Step 1: Create testing checklist**

Create `docs/testing-checklist.md`:

```markdown
# Testing Checklist

## Pre-Deployment Tests

### Data Pipeline
- [ ] Python scripts run without errors locally
- [ ] Databricks connection succeeds with provided token
- [ ] Query returns data for PH and VN
- [ ] Metrics calculations are accurate (spot check)
- [ ] JSON files are generated correctly
- [ ] Historical backfill completes successfully

### GitHub Actions
- [ ] Workflow syntax is valid
- [ ] DATABRICKS_TOKEN secret is configured
- [ ] Manual workflow trigger works
- [ ] Data files are committed correctly
- [ ] Workflow runs every 5 minutes on schedule

### Frontend
- [ ] Page loads without errors
- [ ] Data fetches successfully from JSON files
- [ ] Metrics display correctly for PH and VN
- [ ] Comparison tables populate correctly
- [ ] Charts render with proper data
- [ ] Moving averages display correctly
- [ ] Status indicator updates based on data freshness
- [ ] Auto-refresh works (wait 5+ minutes)
- [ ] Retry logic works (test with broken data file)

### Responsive Design
- [ ] Desktop (1920x1080) - side-by-side layout
- [ ] Tablet (768x1024) - stacked layout
- [ ] Mobile (375x667) - single column

### Cross-Browser
- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)

## Post-Deployment Tests

### Day 1
- [ ] Dashboard loads at GitHub Pages URL
- [ ] Initial data displays correctly
- [ ] First scheduled update runs successfully (check Actions)
- [ ] Data updates after 5 minutes
- [ ] No console errors

### Day 2
- [ ] Week-over-week comparisons are accurate
- [ ] MTD calculations are correct
- [ ] Moving averages are calculating properly
- [ ] Daily history is accumulating

### Day 7
- [ ] 7-day moving average is fully functional
- [ ] Historical data shows proper trends
- [ ] Performance is acceptable (<2s load time)

## Validation Queries

Test metric calculations manually:

### Total GMV (PH Today)
```sql
SELECT SUM(order_gmv) as total_gmv
FROM wh_am.sandbox.orders_live_tracking
WHERE country = 'PH'
AND TO_DATE(DATE_TRUNC('DAY', placement_date)) = CURRENT_DATE
```

### Orders Count (PH Today)
```sql
SELECT COUNT(DISTINCT order_number) as orders
FROM wh_am.sandbox.orders_live_tracking
WHERE country = 'PH'
AND TO_DATE(DATE_TRUNC('DAY', placement_date)) = CURRENT_DATE
```

### Unique Buyers (PH Today)
```sql
SELECT COUNT(DISTINCT account_id) as unique_buyers
FROM wh_am.sandbox.orders_live_tracking
WHERE country = 'PH'
AND TO_DATE(DATE_TRUNC('DAY', placement_date)) = CURRENT_DATE
```

## Known Issues / Notes

- [ ] Document any issues found during testing
- [ ] Note any performance concerns
- [ ] Record any browser-specific quirks
```

**Step 2: Run local validation**

```bash
# Test Python scripts
cd scripts
python extract_data.py

# Verify JSON output
cat ../data/ph.json | python -m json.tool | head -30
cat ../data/vn.json | python -m json.tool | head -30

# Test frontend
cd ..
python -m http.server 8000
# Open http://localhost:8000 and check console
```

Expected: No errors, JSON files created, dashboard displays data

**Step 3: Commit testing documentation**

```bash
git add docs/testing-checklist.md
git commit -m "docs: add testing checklist and validation queries"
```

---

## Task 12: Final Documentation and Deployment Prep

**Files:**
- Create: `docs/deployment-guide.md`
- Create: `docs/maintenance.md`

**Step 1: Create deployment guide**

Create `docs/deployment-guide.md`:

```markdown
# Deployment Guide

## Prerequisites

1. **GitHub Repository**
   - Fork or clone this repository to your GitHub account
   - Ensure GitHub Actions is enabled

2. **Databricks Access**
   - Access token: `dapi6b9bd2e011c8b6ea6282d16aa9082efd-3`
   - Server hostname: `adb-1825183661408911.11.azuredatabricks.net`
   - HTTP path: `sql/protocolv1/o/1825183661408911/0523-172047-4vu5f6v7`

## Deployment Steps

### Step 1: Configure GitHub Secrets

1. Go to your repository on GitHub
2. Navigate to Settings > Secrets and variables > Actions
3. Click "New repository secret"
4. Add the following secret:
   - Name: `DATABRICKS_TOKEN`
   - Value: `dapi6b9bd2e011c8b6ea6282d16aa9082efd-3`

### Step 2: Enable GitHub Pages

1. Go to Settings > Pages
2. Under "Build and deployment":
   - Source: **GitHub Actions**
3. Save the changes

### Step 3: Run Historical Backfill

1. Go to Actions tab
2. Select "Backfill Historical Data" workflow
3. Click "Run workflow" button
4. Select main branch
5. Click "Run workflow"
6. Wait for completion (should take 2-5 minutes)
7. Verify data files created:
   - Check repository for `data/ph.json` and `data/vn.json`

### Step 4: Deploy Dashboard

1. The Pages deployment should trigger automatically after backfill
2. If not, go to Actions > Deploy to GitHub Pages > Run workflow
3. Wait for deployment to complete
4. Dashboard will be available at:
   - `https://[your-username].github.io/bees_dash/`

### Step 5: Verify Scheduled Updates

1. Wait 5-10 minutes
2. Go to Actions tab
3. Verify "Update Dashboard Data" workflow runs automatically
4. Check that data files are being updated with new commits

## Post-Deployment Verification

### Check Data Pipeline
```bash
# View recent workflow runs
# Go to Actions > Update Dashboard Data
# Verify runs are succeeding every 5 minutes
```

### Check Dashboard
1. Open dashboard URL in browser
2. Open browser console (F12)
3. Verify no JavaScript errors
4. Check that metrics display for both PH and VN
5. Verify charts render properly
6. Confirm status indicator shows "Live" (green)

### Validate Metrics
Run validation queries in Databricks to spot-check calculations:
- See docs/testing-checklist.md for SQL queries

## Troubleshooting

### Workflow Fails with Authentication Error
- Verify DATABRICKS_TOKEN secret is set correctly
- Check token hasn't expired
- Confirm token has access to the table

### No Data Displayed
- Check that backfill completed successfully
- Verify data/ph.json and data/vn.json exist
- Check browser console for fetch errors
- Verify GitHub Pages is serving files (not just HTML)

### Dashboard Shows "Stale" Status
- Check recent workflow runs for failures
- Verify scheduled cron is working
- Check GitHub Actions quotas aren't exceeded

### Charts Not Rendering
- Check browser console for Chart.js errors
- Verify Chart.js CDN is accessible
- Check that daily_history data exists

## Rollback Procedure

If deployment fails:

1. Check Actions logs for errors
2. Fix issues in code
3. Push fixes to main branch
4. Workflows will re-run automatically
5. If needed, manually trigger workflows

## Cost Considerations

**GitHub Actions Minutes:**
- Free tier: 2000 minutes/month
- Usage: ~8 minutes/day (12 runs/hour * 24 hours * 0.5 min/run ≈ 144 min/day)
- Monthly usage: ~4320 minutes
- **Note**: You'll exceed free tier, need to monitor usage or reduce frequency

**Recommendation**: Consider reducing frequency to every 15 minutes to stay within free tier:
- Change cron to: `*/15 * * * *`
- Monthly usage: ~1440 minutes (within free tier)
```

**Step 2: Create maintenance guide**

Create `docs/maintenance.md`:

```markdown
# Maintenance Guide

## Routine Maintenance

### Daily
- Monitor workflow runs in Actions tab
- Check for any failures
- Verify dashboard is updating

### Weekly
- Review error logs in repository
- Spot-check metric accuracy
- Verify moving averages are correct

### Monthly
- Review GitHub Actions usage/costs
- Check for Databricks API changes
- Update dependencies if needed

## Common Maintenance Tasks

### Adjusting Refresh Frequency

Edit `.github/workflows/update-dashboard.yml`:

```yaml
# Change this line
- cron: '*/5 * * * *'  # Every 5 minutes

# To one of these:
- cron: '*/15 * * * *'  # Every 15 minutes
- cron: '*/30 * * * *'  # Every 30 minutes
- cron: '0 * * * *'     # Every hour
```

### Adding New Countries

1. Update `scripts/config.py`:
   ```python
   COUNTRIES = ["PH", "VN", "TH"]  # Add new country code
   ```

2. Update `index.html` - duplicate a country dashboard section

3. Update `app.js` - add new country to data loading

4. Update `styles.css` if needed for layout

### Changing Metrics

To add or modify metrics:

1. Update `scripts/extract_data.py`:
   - Modify `calculate_metrics()` function
   - Add new calculation logic

2. Update `index.html`:
   - Add new metric cards
   - Update comparison table

3. Update `app.js`:
   - Add new metric to rendering logic

### Updating Historical Data Window

Edit `scripts/config.py`:

```python
HISTORY_DAYS = 90  # Change from 60 to 90 days
```

Re-run backfill workflow to populate additional history.

### Rotating Databricks Token

1. Generate new token in Databricks
2. Update GitHub Secret:
   - Settings > Secrets > DATABRICKS_TOKEN
   - Update value
3. No code changes needed

## Troubleshooting Common Issues

### Issue: Workflow runs but no data updates

**Symptoms**:
- Workflow shows success
- Data files not updated

**Solution**:
```bash
# Check if git commit is working
# Look at workflow logs for "No changes to commit" message
# May indicate Databricks returned no new data
```

### Issue: Dashboard shows incorrect metrics

**Symptoms**:
- Numbers don't match Databricks queries
- Calculations seem off

**Solution**:
1. Run validation queries (see docs/testing-checklist.md)
2. Check `calculate_metrics()` function logic
3. Verify data filtering in queries

### Issue: Charts not showing moving averages

**Symptoms**:
- Charts render but MA lines are flat or missing

**Solution**:
1. Check `calculate_moving_average()` function
2. Verify sufficient historical data exists (need 7+ days for 7-day MA)
3. Check browser console for calculation errors

### Issue: High GitHub Actions usage

**Symptoms**:
- Approaching or exceeding free tier minutes

**Solution**:
1. Reduce cron frequency to every 15-30 minutes
2. Optimize Python script runtime
3. Consider caching dependencies in workflow

## Performance Optimization

### Frontend Performance
- JSON files should stay under 100KB each
- If larger, consider:
  - Reducing historical data window
  - Compressing JSON in workflow
  - Using gzip encoding

### Backend Performance
- Databricks queries should complete in <30 seconds
- If slower:
  - Add table indexes
  - Optimize SQL queries
  - Consider query result caching

## Monitoring Checklist

Weekly monitoring tasks:

- [ ] Check workflow success rate (should be >95%)
- [ ] Verify data freshness (status indicator green)
- [ ] Spot-check metric accuracy vs. Databricks
- [ ] Review error logs
- [ ] Check GitHub Actions usage
- [ ] Verify dashboard load time (<2 seconds)
- [ ] Test on multiple browsers/devices

## Emergency Procedures

### Dashboard Down
1. Check GitHub Pages status
2. Verify workflows are running
3. Check for repository access issues
4. Manual workflow trigger if needed

### Data Pipeline Failure
1. Check Databricks connectivity
2. Verify token validity
3. Check table permissions
4. Review workflow logs
5. Manual backfill if needed

### Incorrect Data Displayed
1. Stop automatic updates (disable workflow)
2. Investigate data source
3. Fix calculation logic
4. Run manual backfill
5. Re-enable workflow

## Upgrade Path

Future enhancements to consider:

1. **Real-time updates**: WebSocket connection to Databricks
2. **User authentication**: Restrict dashboard access
3. **More countries**: Expand beyond PH and VN
4. **Custom date ranges**: User-selectable time periods
5. **Export functionality**: Download data as CSV/Excel
6. **Alerting**: Email/Slack notifications for anomalies
7. **Mobile app**: Native iOS/Android versions
```

**Step 3: Commit documentation**

```bash
git add docs/deployment-guide.md docs/maintenance.md
git commit -m "docs: add deployment and maintenance guides"
```

---

## Task 13: Push to GitHub and Deploy

**Files:**
- N/A (deployment task)

**Step 1: Create GitHub repository**

```bash
# If repository doesn't exist on GitHub yet:
# 1. Go to github.com
# 2. Click "New repository"
# 3. Name: bees_dash
# 4. Make it private (contains sensitive data/token)
# 5. Don't initialize with README (we already have one)
# 6. Create repository
```

**Step 2: Add remote and push**

```bash
# Add remote (replace YOUR_USERNAME with actual username)
git remote add origin https://github.com/YOUR_USERNAME/bees_dash.git

# Push all code
git push -u origin main

# Verify all files pushed
git log --oneline
```

Expected: All commits pushed to GitHub

**Step 3: Configure GitHub Secrets**

1. Go to repository Settings
2. Secrets and variables > Actions
3. New repository secret:
   - Name: `DATABRICKS_TOKEN`
   - Value: `dapi6b9bd2e011c8b6ea6282d16aa9082efd-3`

**Step 4: Enable GitHub Pages**

1. Settings > Pages
2. Build and deployment:
   - Source: **GitHub Actions**
3. Save

**Step 5: Run backfill workflow**

1. Actions tab
2. Select "Backfill Historical Data"
3. Run workflow > main branch
4. Wait for completion
5. Verify data files committed

**Step 6: Verify deployment**

1. Go to Actions tab
2. Check "Deploy to GitHub Pages" workflow ran
3. Get dashboard URL from workflow output
4. Open URL in browser
5. Verify dashboard displays data

**Step 7: Monitor first update cycle**

1. Wait 5-10 minutes
2. Check "Update Dashboard Data" workflow runs
3. Verify data files updated with new commit
4. Refresh dashboard and check new timestamp

---

## Completion Checklist

### Code Complete
- [ ] All Python scripts working
- [ ] GitHub Actions workflows configured
- [ ] Frontend HTML/CSS/JS complete
- [ ] All files committed to git

### Deployed
- [ ] Code pushed to GitHub
- [ ] Secrets configured
- [ ] GitHub Pages enabled
- [ ] Backfill completed
- [ ] Dashboard accessible at URL
- [ ] Automatic updates working

### Tested
- [ ] Data pipeline runs successfully
- [ ] Metrics calculations verified
- [ ] Dashboard displays correctly
- [ ] Charts render properly
- [ ] Responsive design works
- [ ] Auto-refresh functions

### Documented
- [ ] README complete
- [ ] Deployment guide written
- [ ] Maintenance guide written
- [ ] Testing checklist created

### Handoff to VP
- [ ] Dashboard URL shared
- [ ] Brief demo/walkthrough
- [ ] Explain key metrics
- [ ] Show refresh behavior
- [ ] Provide contact for issues

## Notes

- **Security**: Repository should be private (contains Databricks token)
- **Costs**: Monitor GitHub Actions usage (may exceed free tier at 5-min frequency)
- **Support**: See docs/maintenance.md for ongoing support tasks
- **Enhancements**: See maintenance guide for future improvement ideas
