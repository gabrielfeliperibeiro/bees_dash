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
