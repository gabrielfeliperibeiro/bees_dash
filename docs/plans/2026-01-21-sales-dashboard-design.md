# Sales Dashboard - Real-Time Design Document

**Date:** 2026-01-21
**Project:** Real-time Sales Dashboard for VP
**Countries:** Philippines (PH), Vietnam (VN)

## Overview

A real-time sales dashboard that displays key sales metrics for PH and VN markets side-by-side, with automatic data updates every 5 minutes from Databricks. Built using GitHub Actions for data pipeline and GitHub Pages for hosting.

## System Architecture

### High-Level Architecture

1. **Data Pipeline (GitHub Actions):**
   - Workflow runs every 5 minutes via cron schedule
   - Python script connects to Databricks SQL endpoint using provided token
   - Queries `wh_am.sandbox.orders_live_tracking` for PH and VN
   - Calculates all metrics (GMV, AOV, buyers, frequency, GMV/POCs, moving averages)
   - Generates JSON files with current and historical data
   - Commits JSON files to `data/` directory in the repo
   - One-time backfill script to load 60 days of historical data initially

2. **Frontend (GitHub Pages):**
   - Single HTML page with modern, clean design
   - Side-by-side layout: PH on left, VN on right
   - Vanilla JavaScript (ES6+)
   - Chart.js for visualizations
   - Fetches latest JSON data from `data/` directory
   - Auto-refreshes every 5 minutes to match data updates

3. **Data Storage:**
   - JSON files stored in GitHub repo under `data/ph.json` and `data/vn.json`
   - Each file contains: today's metrics, last week's metrics, MTD metrics, daily historical data (60 days), moving averages
   - Small file sizes (< 100KB each) for fast loading

## Data Structure

### Databricks Connection Details

- **Server Hostname:** `adb-1825183661408911.11.azuredatabricks.net`
- **Port:** 443
- **Protocol:** HTTPS
- **HTTP Path:** `sql/protocolv1/o/1825183661408911/0523-172047-4vu5f6v7`
- **Token:** Stored in GitHub Secrets as `DATABRICKS_TOKEN`

### Source Table Schema

**Table:** `wh_am.sandbox.orders_live_tracking`

Key columns:
- `country`: Filter for 'PH' or 'VN'
- `placement_date`: Order timestamp
- `order_number`: Unique order identifier
- `order_gmv`: Order value in local currency
- `order_gmv_usd`: Order value in USD
- `account_id`: Buyer/customer identifier
- `vendor_account_id`: Vendor/seller identifier (POC)
- `order_status`: Order state (PLACED, INVOICED, etc.)

### JSON Output Structure

Each country file (`data/ph.json`, `data/vn.json`):

```json
{
  "last_updated": "2026-01-21T12:35:00Z",
  "today": {
    "date": "2026-01-21",
    "total_gmv": 125430.50,
    "orders": 342,
    "unique_buyers": 298,
    "unique_vendors": 45,
    "aov": 366.73,
    "frequency": 1.15,
    "gmv_per_poc": 2787.34
  },
  "same_day_last_week": {
    "date": "2026-01-14",
    "total_gmv": 118200.00,
    "orders": 320,
    "unique_buyers": 285,
    "unique_vendors": 43,
    "aov": 369.38,
    "frequency": 1.12,
    "gmv_per_poc": 2748.84
  },
  "mtd": {
    "start_date": "2026-01-01",
    "end_date": "2026-01-21",
    "total_gmv": 2450000.00,
    "orders": 6840,
    "unique_buyers": 5234,
    "unique_vendors": 156,
    "aov": 358.19,
    "frequency": 1.31,
    "gmv_per_poc": 15705.13
  },
  "daily_history": [
    {"date": "2026-01-20", "total_gmv": 120000, "orders": 330, "unique_buyers": 290, "unique_vendors": 44, "aov": 363.64, "frequency": 1.14, "gmv_per_poc": 2727.27},
    {"date": "2026-01-19", "total_gmv": 115000, "orders": 315, "unique_buyers": 280, "unique_vendors": 42, "aov": 365.08, "frequency": 1.13, "gmv_per_poc": 2738.10}
  ],
  "moving_averages": {
    "ma_7d": {
      "gmv": 120500,
      "orders": 335,
      "aov": 359.70,
      "unique_buyers": 295,
      "frequency": 1.14,
      "gmv_per_poc": 2750.00
    },
    "ma_30d": {
      "gmv": 118000,
      "orders": 328,
      "aov": 360.00,
      "unique_buyers": 290,
      "frequency": 1.13,
      "gmv_per_poc": 2700.00
    }
  }
}
```

## Metrics Calculations

### Primary Metrics

1. **Total GMV**: Sum of `order_gmv` for all orders
2. **Orders**: Count of distinct `order_number`
3. **Unique Buyers**: Count of distinct `account_id`
4. **Unique Vendors (POCs)**: Count of distinct `vendor_account_id`
5. **AOV (Average Order Value)**: Total GMV / Orders
6. **Frequency**: Orders / Unique Buyers
7. **GMV/POCs**: Total GMV / Unique Vendors

### Time-Based Calculations

- **Today**: Filter `TO_DATE(DATE_TRUNC('DAY', placement_date)) = CURRENT_DATE`
- **Same Day Last Week**: Current date - 7 days
- **MTD**: Filter `DATE_TRUNC('MONTH', placement_date) = DATE_TRUNC('MONTH', CURRENT_DATE)`
- **7-Day Moving Average**: Rolling average of last 7 days from daily_history
- **30-Day Moving Average**: Rolling average of last 30 days from daily_history

## Frontend UI Design

### Layout Structure

**Header:**
- Logo/Title: "Sales Dashboard - Real-Time"
- Last updated timestamp with auto-refresh indicator
- Health status indicator (Green/Yellow/Red based on data freshness)

**Main Content (Side-by-Side):**

Each country section (PH left, VN right) contains:

1. **Hero Metrics Row** (Large Cards):
   - Total GMV (with % change vs last week, colored badge)
   - Orders (with % change)
   - AOV (with % change)
   - Each card shows: current value, percentage badge (green/red), mini sparkline

2. **Secondary Metrics Row** (Medium Cards):
   - Unique Buyers
   - Frequency
   - GMV/POCs
   - Same styling as hero metrics

3. **Comparison Table**:
   - Columns: Metric | Today | Same Day Last Week | Change | MTD
   - Rows: GMV, Orders, Buyers, AOV, Frequency, GMV/POCs
   - Color-coded changes (green up arrows, red down arrows)

4. **Trend Charts** (Line Charts):
   - Daily GMV trend (30 days) with 7d and 30d moving average overlays
   - Daily Orders trend with moving averages
   - Smooth curves, gridlines, tooltips on hover

### Visual Style

- **Color Scheme:**
  - Dark background: #1a1a1a to #0f0f0f gradient
  - Cards: #252525 with subtle shadows
  - Purple/blue gradient accents (#8b5cf6 to #3b82f6) for positive trends
  - Red accents (#ef4444) for negative trends
  - Yellow/orange (#f59e0b) for highlights and warnings

- **Typography:**
  - Font: Inter (Google Fonts)
  - Headers: 600 weight
  - Body: 400 weight
  - Numbers: Tabular figures for alignment

- **Layout:**
  - Desktop: Side-by-side split (50/50)
  - Tablet: Stacked vertically
  - Mobile: Single column, swipeable

## GitHub Actions Workflow

### Workflow Configuration

**File:** `.github/workflows/update-dashboard.yml`

**Schedule:**
- Cron: `*/5 * * * *` (every 5 minutes)
- Manual trigger: `workflow_dispatch`
- Auto-trigger: Push to main

**Steps:**

1. **Setup Environment:**
   ```yaml
   - Checkout repository
   - Setup Python 3.11
   - Install dependencies from scripts/requirements.txt
   ```

2. **Extract Data:**
   ```yaml
   - Run scripts/extract_data.py
   - Environment variables:
     - DATABRICKS_TOKEN (from GitHub Secrets)
     - DATABRICKS_SERVER_HOSTNAME
     - DATABRICKS_HTTP_PATH
   - Queries PH and VN data
   - Generates data/ph.json and data/vn.json
   ```

3. **Commit & Push:**
   ```yaml
   - Configure git (bot identity)
   - Add data/*.json
   - Commit with timestamp
   - Push to main branch
   - GitHub Pages auto-deploys
   ```

### Backfill Script

**File:** `scripts/backfill_historical.py`

- Run once manually via workflow_dispatch
- Queries last 60 days of data from Databricks
- Generates complete daily_history for both countries
- Creates initial JSON structure

## Error Handling & Monitoring

### Data Pipeline Error Handling

1. **Databricks Connection Failures:**
   - **Retry logic: 3 attempts within 30 seconds**
     - Attempt 1: Immediate
     - Attempt 2: After 10 seconds
     - Attempt 3: After 20 seconds
   - If all retries fail: log error, skip update, keep previous data
   - GitHub Actions shows failed status

2. **Data Quality Checks:**
   - Validate query results not empty
   - Check for anomalies (>50% sudden drops)
   - Flag anomalies with `"data_warning": true` in JSON
   - Dashboard shows warning indicator

3. **Calculation Errors:**
   - Handle division by zero gracefully
   - Missing comparison data: show "N/A"
   - Date mismatches: fall back to available data

### Frontend Error Handling

1. **Data Loading Failures:**
   - Show loading spinner initially
   - **Frontend retry: 3 attempts within 30 seconds**
   - If all fail: show error message with manual retry button

2. **Stale Data Detection:**
   - Check `last_updated` timestamp
   - >10 minutes old: yellow warning indicator
   - >30 minutes old: red alert indicator

3. **Browser Compatibility:**
   - Graceful degradation for older browsers
   - Fallback to simpler charts if Chart.js fails

### Monitoring

- GitHub Actions email notifications on failures
- Log files in `logs/` directory with timestamps
- Dashboard health indicator:
  - Green: Updated <10 min ago
  - Yellow: Updated 10-30 min ago
  - Red: Updated >30 min ago

## Technology Stack

### Backend (Python)
- Python 3.11
- databricks-sql-connector
- pandas
- python-dateutil
- json (built-in)

### Frontend
- HTML5 + CSS3
- Vanilla JavaScript (ES6+)
- Chart.js 4.x
- CSS Grid + Flexbox
- Google Fonts (Inter)

### Infrastructure
- GitHub Actions (CI/CD)
- GitHub Pages (hosting)
- GitHub Secrets (credential storage)

## File Structure

```
bees_dash/
├── .github/
│   └── workflows/
│       └── update-dashboard.yml
├── data/
│   ├── ph.json
│   └── vn.json
├── scripts/
│   ├── extract_data.py
│   ├── backfill_historical.py
│   └── requirements.txt
├── docs/
│   └── plans/
│       └── 2026-01-21-sales-dashboard-design.md
├── logs/
│   └── .gitkeep
├── index.html
├── styles.css
├── app.js
├── README.md
└── .gitignore
```

## Implementation Phases

### Phase 1: Data Pipeline Setup
- Create Python scripts for data extraction
- Configure Databricks connection
- Implement metric calculations
- Setup GitHub Actions workflow
- Run historical backfill

### Phase 2: Frontend Development
- Build HTML structure
- Implement CSS styling (dark theme, cards, responsive)
- Develop JavaScript data fetching and rendering
- Integrate Chart.js for visualizations
- Add auto-refresh functionality

### Phase 3: Testing & Deployment
- Test data pipeline with real Databricks data
- Verify metric calculations accuracy
- Test frontend across browsers
- Configure GitHub Pages
- Monitor first 24 hours of live data

### Phase 4: Refinement
- Adjust refresh rates if needed
- Fine-tune UI based on VP feedback
- Optimize performance
- Add additional metrics if requested

## Success Criteria

- Dashboard updates every 5 minutes with fresh data
- All metrics calculate correctly (GMV, AOV, buyers, frequency, GMV/POCs)
- Side-by-side view clearly shows PH and VN separately
- Comparisons (WoW, MTD) display accurately
- Moving averages (7d, 30d) render smoothly
- UI loads in <2 seconds
- Mobile responsive
- Zero downtime during updates
