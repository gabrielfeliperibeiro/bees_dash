# BEES Dashboard - Quick Reference

## 🚨 Current Issues & Solutions

### Issue 1: GitHub Actions Schedule Delays ⏰

**Problem:** Workflow scheduled every 5 minutes, but runs every 8-30 minutes
**Cause:** GitHub Actions queues scheduled workflows during high load

**Solutions (pick one):**

| Solution | Setup Time | Reliability | Link |
|----------|-----------|-------------|------|
| **External Cron** ⭐ | 5 mins | 100% | [RELIABLE_UPDATES_SOLUTION.md](RELIABLE_UPDATES_SOLUTION.md) |
| Manual Script | 0 mins | Manual | Run `./manual-update.sh` |

### Issue 2: GitHub Pages Deployment Delays 🐌

**Problem:** Data committed but dashboard shows old data for 5-15 minutes
**Cause:** GitHub Pages for private repos has slow deployment queue

**Solutions (pick one):**

| Solution | Deployment Time | Setup Time | Link |
|----------|----------------|-----------|------|
| **Vercel** ⭐ | ~30 seconds | 5 mins | [DEPLOYMENT_FIX.md](DEPLOYMENT_FIX.md) |
| Netlify | ~30 seconds | 5 mins | [DEPLOYMENT_FIX.md](DEPLOYMENT_FIX.md) |
| Cloudflare Pages | ~20 seconds | 10 mins | [DEPLOYMENT_FIX.md](DEPLOYMENT_FIX.md) |
| GitHub Pages | 5-15 minutes | Current | ❌ Not recommended |

---

## ⚡ Quick Actions

### Manual Update Right Now
```bash
./manual-update.sh
```

### Check Last Update Time
```bash
cat data/data-manifest.json | jq '.timestamp'
```

### View Recent Workflow Runs
```bash
gh run list --workflow=update-dashboard.yml --limit 10
```

### Trigger Workflow Manually
```bash
gh workflow run update-dashboard.yml
```

---

## 📊 Current Status (Updated Every 5 Minutes*)

**🇵🇭 Philippines:**
- Latest: 3,839 orders
- GMV: $64,623.82 USD
- Last updated: 05:57 UTC

**🇻🇳 Vietnam:**
- Latest: 33 orders
- GMV: $2,026.81 USD
- Last updated: 05:57 UTC

*\*May be delayed due to GitHub Actions scheduling issues*

---

## 🎯 Recommended Setup (Total: 10 minutes)

**Step 1: Fix Schedule Delays (5 mins)**
1. Go to https://cron-job.org/en/
2. Sign up (free, no credit card)
3. Follow [RELIABLE_UPDATES_SOLUTION.md](RELIABLE_UPDATES_SOLUTION.md)

**Step 2: Fix Deployment Delays (5 mins)**
1. Go to https://vercel.com
2. Import your repo
3. Follow [DEPLOYMENT_FIX.md](DEPLOYMENT_FIX.md)

**Result:**
- Data updates: Every 5 minutes (exactly) ✅
- Deployment: ~30 seconds ✅
- **Total delay: ~30 seconds** (vs current ~30 minutes!)

---

## 🔧 Files in This Repo

| File | Purpose |
|------|---------|
| `manual-update.sh` | Manually trigger data update |
| `RELIABLE_UPDATES_SOLUTION.md` | Fix GitHub Actions schedule delays |
| `DEPLOYMENT_FIX.md` | Fix GitHub Pages deployment delays |
| `QUICK_REFERENCE.md` | This file |
| `vercel.json` | Vercel configuration |
| `netlify.toml` | Netlify configuration |

---

## 📞 Troubleshooting

**Q: Dashboard shows old data**
1. Check when last workflow ran: `gh run list --workflow=update-dashboard.yml --limit 1`
2. If it ran recently, it's a deployment delay → Deploy to Vercel
3. If it hasn't run, it's a schedule delay → Set up external cron

**Q: Workflow not running every 5 minutes**
- This is normal with GitHub Actions scheduled workflows
- Solution: Set up external cron (see [RELIABLE_UPDATES_SOLUTION.md](RELIABLE_UPDATES_SOLUTION.md))

**Q: How do I force an update right now?**
```bash
./manual-update.sh
```

**Q: Where is the dashboard deployed?**
- Current: https://gabrielfeliperibeiro.github.io/bees_dash/
- After Vercel: https://bees-dash-xxx.vercel.app (you choose)

---

## 🎓 Technical Details

**Data Flow:**
```
Databricks → Python Script → JSON Files → Git Commit → Deployment → Dashboard
  (5 min)      (30 sec)        (instant)    (instant)    (5-15 min*)   (instant)

*Deployment time depends on platform:
- GitHub Pages: 5-15 minutes
- Vercel/Netlify: 30 seconds
```

**Workflow Triggers:**
1. `schedule` - Every 5 minutes (unreliable, 8-30 min delays)
2. `workflow_dispatch` - Manual trigger via GitHub UI or CLI
3. `repository_dispatch` - External API trigger (most reliable)

---

## 💡 Best Practice Recommendation

**For Production Use:**

✅ **DO THIS:**
1. Set up external cron (cron-job.org) → Reliable 5-minute updates
2. Deploy to Vercel → Fast deployments (~30 sec)
3. Keep `manual-update.sh` → Emergency updates

❌ **DON'T RELY ON:**
1. GitHub Actions scheduled workflows → Unreliable timing
2. GitHub Pages for private repos → Slow deployments

**Total Setup Time: 10 minutes**
**Benefit: ~99% reduction in update delay (30 min → 30 sec)**
