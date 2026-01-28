# Vercel Setup - Auto Update Daily

This guide will help you deploy the BEES Dashboard to Vercel with automatic data updates once per day.

**Note**: Vercel Hobby (free) plan only supports daily cron jobs. For more frequent updates (every 15 minutes), you would need to upgrade to Vercel Pro plan.

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

The cron job is configured to run once per day:
- Schedule: `0 2 * * *` (2:00 AM UTC = 10:00 AM Hong Kong time)
- Endpoint: `/api/update-data`
- This triggers the GitHub Actions workflow to update data

**Note**: Hobby plan only supports daily cron jobs. For more frequent updates, see the "Alternatives for More Frequent Updates" section below.

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
│  Daily at 2:00 AM UTC (10:00 AM HK):                   │
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
│                                                         │
│  Note: GitHub Actions also runs hourly (free)         │
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
- Vercel cron: Updates daily at 2:00 AM UTC (10:00 AM Hong Kong)
- GitHub Actions: Updates hourly (already active)
- Format: "Updated: X minutes ago"

---

## Alternatives for More Frequent Updates

Since Vercel Hobby plan only supports daily cron jobs, here are alternatives for more frequent updates:

### Option 1: Manual Updates (Free)
Run the manual update script whenever you need fresh data:
```bash
sh manual-update.sh
```
This is instant and free!

### Option 2: GitHub Actions Hourly (Free)
The GitHub Actions workflow is already configured to run hourly:
- Automatically runs every hour at minute 1 (00:01, 01:01, 02:01, etc.)
- No Vercel cron needed
- Completely free (GitHub Actions free tier: 2,000 minutes/month)
- See: `.github/workflows/update-dashboard.yml`

**This is already active!** Your dashboard updates hourly via GitHub Actions without needing Vercel cron at all.

### Option 3: Upgrade to Vercel Pro ($20/month)
- Supports cron jobs running every minute
- Change schedule to `*/15 * * * *` for 15-minute updates
- Includes more bandwidth and function execution time

## Cost Estimate

**Vercel Hobby (Free) Tier**:
- ✅ Daily cron jobs
- ✅ Serverless Functions: 100 GB-hours/month
- ✅ Bandwidth: 100 GB/month
- ✅ Your setup is well within free tier limits

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
