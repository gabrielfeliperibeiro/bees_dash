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
