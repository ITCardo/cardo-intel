# ⚙️ GitHub Actions Automation Setup

Your automated daily research workflow is ready to deploy! Follow these steps to enable it.

## What's Been Created

✅ **GitHub Actions Workflow** — `.github/workflows/daily-refresh.yml`
- Runs daily at 9 AM UTC (configurable)
- Calls all 6 research agents
- Builds and publishes dashboard automatically

✅ **Python Scripts** — `scripts/` directory
- `research_agent.py` — Gathers brand-specific competitive intelligence
- `social_media_listener.py` — Collects customer feedback from forums
- `product_expert.py` — Synthesizes strategic insights

✅ **Documentation** — `docs/GITHUB_ACTIONS.md`
- Complete setup guide with examples
- Troubleshooting tips
- Customization options

---

## Step 1: Push Code to GitHub

The workflow files need to be pushed to GitHub to be recognized.

### Option A: Push via GitHub CLI (Recommended)

```bash
# Refresh authentication with workflow scope
gh auth logout
gh auth login -h github.com

# When prompted:
# 1. Select "HTTPS"
# 2. Select "Paste an authentication token"
# 3. Go to https://github.com/settings/tokens/new
# 4. Create token with scopes: repo, workflow
# 5. Paste token into CLI

# Then push:
cd /Users/guyw/Desktop/Claude/Cardo
git push origin main
```

### Option B: Push via Web Browser

1. Go to https://github.com/ITCardo/cardo-intel
2. Click **+** button, select "Upload files"
3. Drag and drop:
   - `.github/workflows/daily-refresh.yml`
   - `scripts/research_agent.py`
   - `scripts/social_media_listener.py`
   - `scripts/product_expert.py`
4. Commit with message: "Add GitHub Actions automation for daily refresh"

---

## Step 2: Add GitHub Secrets

The workflow needs API keys to function.

### Add Anthropic API Key

1. Go to https://github.com/ITCardo/cardo-intel/settings/secrets/actions
2. Click **"New repository secret"**
3. Name: `ANTHROPIC_API_KEY`
4. Value: Your Claude API key from https://console.anthropic.com
5. Click **"Add secret"**

### Add Firecrawl API Key (Optional but Recommended)

1. Click **"New repository secret"** again
2. Name: `FIRECRAWL_API_KEY`
3. Value: Your Firecrawl key from https://firecrawl.dev
4. Click **"Add secret"**

**Note:** Both secrets are now encrypted in GitHub and will be passed to the workflow.

---

## Step 3: Enable GitHub Actions (if needed)

1. Go to https://github.com/ITCardo/cardo-intel/settings/actions
2. Ensure "Allow all actions and reusable workflows" is selected
3. Click **Save**

---

## Step 4: Verify Workflow

### Check if workflow is active

1. Go to https://github.com/ITCardo/cardo-intel/actions
2. Look for **"Daily Competitive Research Refresh"** workflow
3. If you see it, the workflow is installed! ✅

### Manually trigger first run (recommended for testing)

1. Click **"Daily Competitive Research Refresh"** workflow
2. Click **"Run workflow"** button (top right)
3. Select branch "main"
4. Click **"Run workflow"**

The workflow will start immediately. Check the logs to verify it works.

### Monitor the run

1. Wait 15-20 minutes for the full workflow to complete
2. Watch the logs for:
   - ✅ Research agents updating JSON files
   - ✅ Social Media Listener finding customer feedback
   - ✅ Product Expert generating insights
   - ✅ Dashboard rebuilt successfully
   - ✅ Changes committed and pushed

---

## Step 5: Automatic Schedule Starts

Once the workflow is pushed and secrets are added:

- **Default:** Runs daily at **9 AM UTC** 
- Check the Actions tab for scheduled runs
- First automatic run happens at the next 9 AM UTC
- All subsequent days at the same time

---

## Customization

### Change Run Time

Edit `.github/workflows/daily-refresh.yml`, line 7:

```yaml
on:
  schedule:
    - cron: '0 14 * * *'  # Change to 2 PM UTC
```

Common times:
- `0 9 * * *` = 9 AM UTC (4 AM EST)
- `0 14 * * *` = 2 PM UTC (9 AM EST)
- `0 0 * * *` = Midnight UTC (7 PM EST)

Push the change and it takes effect immediately.

---

## Cost

- **Anthropic API:** ~$0.07/day = ~$2/month
  - 6 calls × 4000 tokens average × $0.003/1K tokens
- **GitHub Actions:** Free (included with GitHub account)
- **Total:** ~$2/month for fully automated daily intelligence

---

## What Happens Automatically Now

```
Every day at 9 AM UTC:
┌─────────────────────────────────────────┐
│ GitHub Actions Workflow Starts           │
├─────────────────────────────────────────┤
│ 1. Check out latest code                 │
│ 2. Install Python dependencies           │
│ 3. Configure Git                         │
│                                          │
│ 4. Cardo Research Agent                  │
│    └─ Updates research/cardo.json        │
│ 5. Sena Research Agent                   │
│    └─ Updates research/sena.json         │
│ 6. ASMAX Research Agent                  │
│    └─ Updates research/asmax.json        │
│ 7. Reso Research Agent                   │
│    └─ Updates research/reso.json         │
│ 8. Social Media Listener                 │
│    └─ Appends customer_feedback to all   │
│ 9. Product Expert Agent                  │
│    └─ Regenerates product_insights.json  │
│                                          │
│ 10. Build Dashboard                      │
│     └─ Runs build.py → dashboard.html    │
│ 11. Commit & Push                        │
│     └─ Commits changes to main branch    │
│ 12. Verify Deployment                    │
│     └─ Confirms GitHub Pages is live     │
│                                          │
│ Dashboard updated at:                    │
│ https://itcardo.github.io/cardo-intel/ │
└─────────────────────────────────────────┘
```

---

## Troubleshooting

### Workflow doesn't show in Actions tab

**Fix:** Push the `.github/workflows/daily-refresh.yml` file to GitHub (Step 1)

### "API key not found" error in logs

**Fix:** Add secrets to GitHub Settings → Secrets and variables → Actions (Step 2)

### Workflow fails with JSON error

**Fix:** Check the full logs, likely Claude API had a network issue. Manually re-run.

### Dashboard not updating

**Fix:** Hard refresh browser (Cmd+Shift+R), wait 30-60 seconds for GitHub Pages

### No automatic runs happening

**Fix:** Verify:
1. Workflow file is pushed to GitHub
2. Branch is `main`
3. Repo has commits in the past 60 days (GitHub requirement for scheduled workflows)

---

## What You Can Do Now

✅ **Daily automatic research** — No manual work needed
✅ **Consistent data quality** — Same agents, same standards every day
✅ **Dashboard always current** — Live at GitHub Pages
✅ **Cost-effective** — ~$2/month for full automation
✅ **Scalable** — Easy to add more brands or data sources

---

## Next Steps

1. **Push code to GitHub** (Step 1 above)
2. **Add API keys as secrets** (Step 2)
3. **Manually trigger first run** to verify it works (Step 4)
4. **Monitor logs** to see agents in action
5. **Customize schedule** if needed (e.g., different run time)
6. **Check dashboard** at https://itcardo.github.io/cardo-intel/ for updates

---

## Documentation

- [docs/GITHUB_ACTIONS.md](docs/GITHUB_ACTIONS.md) — Complete reference guide
- [README.md](README.md) — System overview
- [docs/AGENTS.md](docs/AGENTS.md) — Agent descriptions
- [.github/workflows/daily-refresh.yml](.github/workflows/daily-refresh.yml) — Workflow definition

---

**Questions?** Check `docs/GITHUB_ACTIONS.md` for troubleshooting and more details.
