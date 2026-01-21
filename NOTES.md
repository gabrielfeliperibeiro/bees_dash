# Dashboard Notes

## Scheduled Workflow Updates

The dashboard is configured to update every 5 minutes via GitHub Actions cron schedule (`*/5 * * * *`).

### Known Limitations

**GitHub Actions Scheduled Workflows:**
- Scheduled workflows can be delayed by 5-10 minutes during high-load periods
- Scheduled workflows may be disabled if the repository is inactive for 60 days
- On new/low-activity repositories, schedule may take time to activate
- GitHub may disable schedules if they detect low repository activity

### Current Status

- **Cron Schedule**: Every 5 minutes (`:00, :05, :10, :15, :20, :25, :30, :35, :40, :45, :50, :55`)
- **Manual Trigger**: Available via GitHub Actions UI or `gh workflow run update-dashboard.yml`
- **Fallback**: Push trigger on workflow/script changes

### Manual Update

To manually trigger an update:
```bash
gh workflow run update-dashboard.yml --ref main
```

Or via GitHub UI:
1. Go to Actions tab
2. Select "Update Dashboard Data"
3. Click "Run workflow"
4. Select branch: main
5. Click "Run workflow"

### Monitoring

Check recent runs:
```bash
gh run list --workflow=update-dashboard.yml --limit 10
```

## Data Calculations

### VN AOV and GMV/POC

**Why they're the same:**
- VN currently has: 32 orders, 32 buyers, 32 vendors
- Each vendor has exactly 1 buyer placing 1 order
- AOV = Total GMV / Orders = 110,723,094.25 / 32 = 3,460,096.70
- GMV/POC = Total GMV / Vendors = 110,723,094.25 / 32 = 3,460,096.70
- **This is correct data, not a bug**

### USD Conversion Rates

- **Philippines (PH)**: 56.017 PHP = 1 USD
- **Vietnam (VN)**: 26,416 VND = 1 USD

## Timezone

All times displayed in **Hong Kong Time (UTC+8)** as requested.
Database queries use UTC timestamps.
