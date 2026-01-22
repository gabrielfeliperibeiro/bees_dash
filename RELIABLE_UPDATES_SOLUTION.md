# Reliable Updates Solution - Fix GitHub Actions Schedule Delays

## The Problem

GitHub Actions scheduled workflows (`cron`) are **NOT reliable**:
- Scheduled to run every 5 minutes: `*/5 * * * *`
- **Actually runs**: every 8-30 minutes (sometimes longer)
- Reason: GitHub Actions queues scheduled workflows, causing delays during high load

**Your workflow timing (actual):**
```
05:43:31 → 05:54:27 = 11 minutes ❌
05:54:27 → 06:02:58 = 8 minutes ❌
06:02:58 → 06:32:21 = 29 minutes ❌❌
06:32:21 → 06:55:55 = 23 minutes ❌❌
```

## The Solution: External Cron Service

Use a **reliable external cron service** to trigger your workflow every 5 minutes via GitHub's API.

---

## ⚡ Quick Setup (5 Minutes) - cron-job.org

### Step 1: Get Your GitHub Token

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Name it: `BEES Dashboard Cron Trigger`
4. Select scopes: **ONLY** check `repo` (full control of private repositories)
5. Click **"Generate token"**
6. **COPY THE TOKEN** - you'll need it in the next step

### Step 2: Set Up cron-job.org

1. Go to https://cron-job.org/en/
2. Sign up for free (100% free, no credit card)
3. Click **"Create cronjob"**

**Configuration:**
```
Title: BEES Dashboard Update
URL: https://api.github.com/repos/gabrielfeliperibeiro/bees_dash/dispatches
Schedule: */5 * * * * (every 5 minutes)
Request Method: POST
Request Headers:
  - Header: Authorization
    Value: Bearer YOUR_GITHUB_TOKEN_HERE
  - Header: Accept
    Value: application/vnd.github+json
  - Header: Content-Type
    Value: application/json
Request Body:
{
  "event_type": "update-data"
}
```

4. Click **"Create cronjob"**
5. **Test it**: Click "Run now" to verify it works

### Step 3: Verify It's Working

```bash
# Check if workflow was triggered
gh run list --workflow=update-dashboard.yml --limit 5
```

You should see runs triggered by `repository_dispatch` every 5 minutes.

---

## 📊 Alternative: EasyCron (More Features)

If you want more monitoring and alerting:

1. Go to https://www.easycron.com/
2. Sign up for free (50 cron jobs free)
3. Create new cron job:

```
URL: https://api.github.com/repos/gabrielfeliperibeiro/bees_dash/dispatches
Cron Expression: */5 * * * *
Request Method: POST
HTTP Headers:
  Authorization: Bearer YOUR_GITHUB_TOKEN_HERE
  Accept: application/vnd.github+json
  Content-Type: application/json
POST Data:
  {"event_type": "update-data"}
```

**Benefits:**
- Email alerts if workflow fails
- Execution history
- Success/failure tracking

---

## 🔄 How It Works

**Before (Unreliable):**
```
GitHub Actions Scheduler (delayed) → Workflow runs → Data updates
Problem: 8-30 minute delays
```

**After (Reliable):**
```
External Cron Service (exact timing) → API trigger → Workflow runs → Data updates
Result: Runs exactly every 5 minutes
```

---

## ⚙️ Advanced: Health Check Endpoint

If you deploy to Vercel/Netlify, you can create a health check that shows the last update time:

**Create `api/health.js` (for Vercel):**
```javascript
export default async function handler(req, res) {
  const manifestUrl = 'https://yourdomain.vercel.app/data/data-manifest.json';
  const manifest = await fetch(manifestUrl).then(r => r.json());

  const lastUpdate = new Date(manifest.timestamp);
  const now = new Date();
  const minutesAgo = Math.floor((now - lastUpdate) / 60000);

  res.json({
    status: minutesAgo < 10 ? 'healthy' : 'stale',
    last_update: manifest.timestamp,
    minutes_ago: minutesAgo,
    message: minutesAgo < 10 ? 'Data is fresh' : 'Data is stale - check workflow'
  });
}
```

Then you can monitor: `https://yourdomain.vercel.app/api/health`

---

## 🎯 Recommended Setup

1. **Immediate**: Set up cron-job.org (5 minutes setup)
2. **Next**: Deploy to Vercel for faster deployments (see DEPLOYMENT_FIX.md)
3. **Optional**: Add health check endpoint for monitoring

**With both fixes:**
- External cron → Reliable 5-minute triggers
- Vercel deployment → 30-second deployments (vs 15-minute GitHub Pages)
- **Total delay: ~30 seconds** (vs current ~30 minutes!)

---

## 🔧 Troubleshooting

**Q: How do I know if cron-job.org is working?**
```bash
# Check recent workflow runs
gh run list --workflow=update-dashboard.yml --limit 10

# Look for "repository_dispatch" as the trigger
```

**Q: Can I disable GitHub's scheduled cron?**
Yes, but keep it as a fallback. The external cron will trigger it more reliably anyway.

**Q: What if I want to use a different service?**
Any service that can make HTTP POST requests works:
- cron-job.org (recommended)
- EasyCron
- UptimeRobot
- Cronitor
- Your own server with cron

Just use the same API endpoint and authentication.

---

## 🚨 Important Security Note

**Your GitHub token has repo access - keep it secure:**
- Don't commit it to git
- Don't share it
- Use minimal permissions (only `repo` scope)
- Rotate it periodically

**The token is only stored in the external cron service - not in your code.**
