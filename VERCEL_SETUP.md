# Vercel Setup - Auto Update Every 15 Minutes

This guide will help you deploy the BEES Dashboard to Vercel with automatic data updates every 15 minutes.

## Prerequisites

- Vercel account (free tier works)
- GitHub account with this repository
- GitHub Personal Access Token (PAT) with `repo` and `workflow` permissions

---

## Step 1: Create GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Or visit: https://github.com/settings/tokens

2. Click **"Generate new token (classic)"**

3. Configure the token:
   - **Note**: `BEES Dashboard - Vercel Cron`
   - **Expiration**: 90 days (or No expiration if you prefer)
   - **Scopes**: Check these boxes:
     - ✅ `repo` (Full control of private repositories)
     - ✅ `workflow` (Update GitHub Action workflows)

4. Click **"Generate token"**

5. **IMPORTANT**: Copy the token immediately (starts with `ghp_...`)
   - You won't be able to see it again!

---

## Step 2: Deploy to Vercel

### Option A: Deploy via Vercel Dashboard (Recommended)

1. Go to [Vercel Dashboard](https://vercel.com/new)

2. Click **"Import Git Repository"**

3. Select your GitHub repository: `gabrielfeliperibeiro/bees_dash`

4. Configure the project:
   - **Framework Preset**: Other
   - **Root Directory**: ./
   - **Build Command**: (leave empty)
   - **Output Directory**: `.` (current directory)

5. Click **"Deploy"**

### Option B: Deploy via Vercel CLI

```bash
npm install -g vercel
cd /path/to/bees_dash
vercel
```

---

## Step 3: Configure Environment Variables

After deployment, add these environment variables in Vercel:

1. Go to your Vercel project → **Settings** → **Environment Variables**

2. Add the following variables:

   | Variable Name | Value | Description |
   |--------------|-------|-------------|
   | `GITHUB_TOKEN` | `ghp_your_token_here` | Your GitHub PAT from Step 1 |
   | `CRON_SECRET` | `generate_random_string` | Random secret for cron security |

3. **For CRON_SECRET**: Generate a random string:
   ```bash
   # On Mac/Linux:
   openssl rand -base64 32

   # Or use any random string generator
   ```

4. Click **"Save"** for each variable

5. Make sure to select **"All"** environments (Production, Preview, Development)

---

## Step 4: Enable Vercel Cron Jobs

Vercel Cron Jobs are automatically enabled when you have a `vercel.json` with `crons` configuration (already included in this project).

The cron job is configured to run every 15 minutes:
- Schedule: `*/15 * * * *`
- Endpoint: `/api/update-data`
- This triggers the GitHub Actions workflow to update data

---

## Step 5: Verify Setup

### Test the Cron Endpoint Manually

You can test the update endpoint:

```bash
curl -X POST https://your-project.vercel.app/api/update-data \
  -H "Authorization: Bearer YOUR_CRON_SECRET"
```

Replace:
- `your-project.vercel.app` with your Vercel domain
- `YOUR_CRON_SECRET` with the value you set in Step 3

Expected response:
```json
{
  "success": true,
  "message": "Data update workflow triggered",
  "timestamp": "2026-01-28T12:00:00.000Z",
  "workflow": "update-dashboard.yml"
}
```

### Check Cron Logs

1. Go to Vercel Dashboard → Your Project → **Logs**
2. Filter by Function: `/api/update-data`
3. You should see logs every 15 minutes showing:
   ```
   [CRON] Triggering data update workflow...
   [CRON] ✅ Workflow triggered successfully
   ```

### Verify GitHub Actions

1. Go to your GitHub repository → **Actions** tab
2. Look for "Update Dashboard Data" workflow runs
3. You should see automatic runs every 15 minutes triggered by Vercel

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│  Every 15 minutes:                                      │
│                                                         │
│  1. Vercel Cron Job                                    │
│     └─> Calls /api/update-data                        │
│                                                         │
│  2. Serverless Function                                │
│     └─> Triggers GitHub Actions via API               │
│                                                         │
│  3. GitHub Actions Workflow                            │
│     ├─> Runs Python script (extract_data.py)         │
│     ├─> Queries Databricks                           │
│     ├─> Updates JSON files                           │
│     └─> Commits & pushes to GitHub                   │
│                                                         │
│  4. Vercel Auto-Deploy                                │
│     └─> Detects GitHub push                          │
│     └─> Deploys updated data (~30 seconds)           │
│                                                         │
│  5. Dashboard Updates                                  │
│     └─> Users see fresh data                         │
└─────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Cron job not running

**Check**: Vercel Dashboard → Settings → Crons
- Make sure cron jobs are enabled
- Verify the schedule shows `*/15 * * * *`

**Solution**: Redeploy the project to register the cron configuration

### "Unauthorized" error

**Issue**: Missing or incorrect `CRON_SECRET`

**Solution**:
1. Verify `CRON_SECRET` is set in Vercel environment variables
2. Make sure it matches exactly (no extra spaces)
3. Redeploy after changing environment variables

### "GITHUB_TOKEN not configured"

**Issue**: Missing GitHub token

**Solution**:
1. Add `GITHUB_TOKEN` to Vercel environment variables
2. Use the token from Step 1 (starts with `ghp_`)
3. Redeploy the project

### GitHub Actions workflow not triggering

**Issue**: Token doesn't have correct permissions

**Solution**:
1. Verify your GitHub token has `repo` and `workflow` scopes
2. Regenerate the token if needed
3. Update `GITHUB_TOKEN` in Vercel
4. Redeploy

### Data not updating on dashboard

**Check**:
1. GitHub Actions → Verify workflow completed successfully
2. Check if data files were updated in GitHub repo
3. Vercel Dashboard → Deployments → Check latest deployment

**Note**: There's a ~30 second delay between GitHub push and Vercel deployment

---

## Monitoring

### View Cron Execution History

Vercel Dashboard → Your Project → Crons → View execution history

### View GitHub Actions Runs

GitHub Repository → Actions → "Update Dashboard Data" workflow

### Check Data Freshness

Dashboard shows "Last Updated" timestamp at the top
- Should update every 15 minutes
- Format: "Updated: X minutes ago"

---

## Cost Estimate

**Vercel Free Tier**:
- ✅ Cron Jobs: 100 hours/month (enough for 15-min intervals)
- ✅ Serverless Functions: 100 GB-hours/month
- ✅ Bandwidth: 100 GB/month

Your setup uses ~2-3 hours/month of cron execution time, well within the free tier.

---

## Next Steps

1. ✅ Deploy to Vercel (Step 2)
2. ✅ Add environment variables (Step 3)
3. ✅ Wait 15 minutes for first automated update
4. ✅ Verify data is updating automatically

---

## Support

If you encounter issues:

1. Check Vercel logs: Dashboard → Logs
2. Check GitHub Actions: Repository → Actions
3. Verify environment variables are set correctly
4. Make sure GitHub token has correct permissions

---

## Manual Update (Optional)

You can still trigger manual updates using the shell script:

```bash
sh manual-update.sh
```

This is useful for:
- Immediate data refresh
- Testing changes
- One-off updates outside the 15-minute schedule
