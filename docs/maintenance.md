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
