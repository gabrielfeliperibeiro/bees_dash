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
