# GitHub Actions Setup Guide

This guide covers setting up automated daily runs using GitHub Actions.

## Overview

The GitHub Actions workflow (`/.github/workflows/daily-refresh.yml`) automatically:

1. **Runs daily at 9 AM UTC** (adjustable via cron schedule)
2. **Spawns all 6 agents** (4 brand researchers + Social Media Listener + Product Expert)
3. **Calls Claude API** via the Anthropic SDK
4. **Builds the dashboard** with updated research
5. **Commits and pushes changes** to GitHub
6. **Publishes to GitHub Pages** automatically

All logs are visible in GitHub Actions tab.

---

## Prerequisites

1. **GitHub account** with repository access (public or private)
2. **Anthropic API key** (Claude API access)
3. **Firecrawl API key** (for web scraping, optional but recommended)

---

## Step 1: Add GitHub Secrets

GitHub Actions requires API keys to be stored as encrypted secrets.

### 1a. Get your API keys

**Anthropic API Key:**
- Go to https://console.anthropic.com
- Copy your API key from the account settings

**Firecrawl API Key (optional):**
- Go to https://firecrawl.dev
- Copy your API key from dashboard

### 1b. Add secrets to GitHub

1. Go to your GitHub repository: https://github.com/YOUR_USERNAME/cardo-intel
2. Navigate to **Settings → Secrets and variables → Actions**
3. Click **"New repository secret"**
4. Add `ANTHROPIC_API_KEY` with your Claude API key
5. Add `FIRECRAWL_API_KEY` with your Firecrawl key (optional)

```
Settings → Secrets and variables → Actions → New repository secret
Name: ANTHROPIC_API_KEY
Value: sk-ant-...your-key...
```

Repeat for `FIRECRAWL_API_KEY`.

---

## Step 2: Verify Workflow File

The workflow file is at: `.github/workflows/daily-refresh.yml`

Key configuration:
```yaml
on:
  schedule:
    - cron: '0 9 * * *'  # 9 AM UTC daily (adjust if needed)
  workflow_dispatch:      # Manual trigger also available
```

### Cron Schedule Examples

| Schedule | Cron |
|----------|------|
| Daily 9 AM UTC | `0 9 * * *` |
| Daily 7 AM UTC | `0 7 * * *` |
| Daily 2 PM UTC | `0 14 * * *` |
| Weekdays 9 AM UTC | `0 9 * * 1-5` |

To change the schedule, edit `.github/workflows/daily-refresh.yml` line 7.

---

## Step 3: Python Scripts Setup

The workflow calls three Python scripts from the `scripts/` directory:

### Script 1: `scripts/research_agent.py`
- Runs once per brand: cardo, sena, asmax, reso
- Updates `research/{brand}.json` with latest data
- Calls Claude API to gather and synthesize research
- Runtime: ~2-3 minutes per brand (8-12 min total for all 4)

**What it does:**
- Searches official websites for products and pricing
- Checks press coverage (motorcycle magazines, YouTube)
- Looks for firmware updates
- Verifies customer sentiment and feedback
- Returns updated JSON

**How it's called:**
```bash
python scripts/research_agent.py cardo
python scripts/research_agent.py sena
python scripts/research_agent.py asmax
python scripts/research_agent.py reso
```

### Script 2: `scripts/social_media_listener.py`
- Collects customer feedback across all brands
- Appends real posts to `customer_feedback[]` in each brand JSON
- Runtime: ~3-4 minutes

**What it does:**
- Searches Reddit r/motorcyclegear for brand mentions
- Attempts to find Facebook group posts (limited, member-gated)
- Classifies sentiment (positive/negative/mixed/neutral)
- Returns feedback organized by brand

**How it's called:**
```bash
python scripts/social_media_listener.py
```

### Script 3: `scripts/product_expert.py`
- Synthesizes insights from ALL research data
- Regenerates `research/product_insights.json` from scratch
- Runtime: ~5-8 minutes

**What it does:**
- Analyzes all brand research + customer feedback
- Identifies strategic gaps
- Generates market pulse (recent moves)
- Recommends prioritized actions
- Flags watchlist signals

**How it's called:**
```bash
python scripts/product_expert.py
```

---

## Step 4: Monitor and Verify

### View Workflow Runs

1. Go to your repository: https://github.com/YOUR_USERNAME/cardo-intel
2. Click **Actions** tab
3. Select **"Daily Competitive Research Refresh"** workflow
4. View the latest run

### Check Logs

Each step logs its progress:
- ✅ Step completed successfully
- ❌ Step failed (with error details)
- ⚠️ Step had warnings (continued anyway)

### Example Successful Run

```
✅ Checkout code
✅ Set up Python
✅ Install dependencies
✅ Configure Git
✅ Run Cardo research agent
   (Claude API called, updated research/cardo.json)
✅ Run Sena research agent
   (Claude API called, updated research/sena.json)
✅ Run ASMAX research agent
✅ Run Reso research agent
✅ Run Social Media Listener agent
   (Added 15 new customer feedback entries across brands)
✅ Run Product Expert agent
   (Regenerated research/product_insights.json)
✅ Build dashboard
   (build.py generated dashboard.html + index.html)
✅ Validate JavaScript
✅ Commit and push changes
   (Pushed to main branch)
✅ Verify deployment
   ✅ Dashboard is live at https://itcardo.github.io/cardo-intel/
```

### If Run Fails

Check the logs for:

1. **API Key Issues**
   - Verify secrets are set correctly in GitHub Settings
   - Ensure API key has sufficient credits/quota

2. **JSON Parsing Errors**
   - Claude response may have been malformed
   - Check research JSON files for syntax errors
   - Fix manually if needed, re-run workflow

3. **Git Push Failures**
   - Usually branch conflicts or permission issues
   - Verify GITHUB_TOKEN permissions
   - Check for uncommitted changes

4. **Network/Timeout Issues**
   - GitHub Actions may have network issues
   - Workflow automatically retries failed steps
   - Check if external services (Claude API) are down

---

## Step 5: Manual Trigger

To run the workflow manually without waiting for the schedule:

1. Go to **Actions** tab
2. Select **"Daily Competitive Research Refresh"** workflow
3. Click **"Run workflow"** button
4. Select branch (usually "main")
5. Click **"Run workflow"**

The workflow will start immediately.

---

## Customization

### Change Run Time

Edit `.github/workflows/daily-refresh.yml`:

```yaml
on:
  schedule:
    - cron: '0 14 * * *'  # Change from 9 AM to 2 PM UTC
```

Common times:
- **9 AM UTC** = `0 9 * * *` (4 AM EST / 1 AM PST)
- **2 PM UTC** = `0 14 * * *` (9 AM EST / 6 AM PST)
- **Midnight UTC** = `0 0 * * *` (7 PM EST / 4 PM PST)

### Skip Some Agents

To skip an agent (e.g., during testing), comment out its step:

```yaml
      # - name: Run Sena research agent
      #   env:
      #     ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      #   run: |
      #     python scripts/research_agent.py sena
```

### Add Notifications

To get notified of failures, add a step before the `notify-failure` job:

```yaml
      - name: Notify Slack on failure
        if: failure()
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"Cardo daily refresh failed"}' \
            ${{ secrets.SLACK_WEBHOOK }}
```

Add `SLACK_WEBHOOK` as a GitHub secret.

---

## Troubleshooting

### Workflow doesn't run on schedule

**Issue:** Scheduled workflow hasn't run at the expected time
**Cause:** GitHub Actions scheduled workflows only run if there's been a commit in the past 60 days
**Fix:** Make sure there's activity in the repo; push a commit if needed

### "API key not found" error

**Issue:** Workflow fails with `ANTHROPIC_API_KEY not found`
**Cause:** Secret not set in GitHub Settings
**Fix:** 
1. Go to Settings → Secrets and variables → Actions
2. Verify `ANTHROPIC_API_KEY` and `FIRECRAWL_API_KEY` are present
3. Re-run the workflow

### JSON validation errors

**Issue:** `research/cardo.json` has invalid JSON
**Cause:** Claude API returned malformed JSON or network issue
**Fix:** 
1. Check the full log for details
2. Fix the JSON manually if needed
3. Re-run the workflow

### Changes not pushed to GitHub

**Issue:** Workflow completes but no changes on GitHub
**Cause:** No new data was gathered (all existing data was current)
**Expected:** Workflow skips commit if no changes detected
**Verify:** Check git status in the workflow logs - should say "No changes detected"

### Dashboard not updating

**Issue:** Live site at GitHub Pages shows old data
**Cause:** GitHub Pages cache or delayed rebuild
**Fix:**
1. Hard refresh browser: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
2. Clear browser cache
3. Wait 30-60 seconds for GitHub Pages to rebuild
4. Verify commit was pushed: `git log -1` in repo should show today's refresh

---

## Cost Considerations

### Anthropic API Usage

Each daily run calls Claude API 6 times (one per agent + Product Expert):
- **4 research agents** × 4000 tokens average = 16,000 tokens
- **1 social listener** × 4000 tokens = 4,000 tokens
- **1 product expert** × 4000 tokens = 4,000 tokens
- **Total: ~24,000 tokens per day**

At Anthropic's current pricing (~$0.003 per 1K tokens for Opus):
- **~$0.07 per day = ~$2/month**

Very economical for automated intelligence.

### GitHub Actions

GitHub Actions is free for public repositories and includes 2,000 minutes/month for private repos.

Each daily run takes ~5-10 minutes → ~150-300 minutes/month (well within free tier).

---

## Security Best Practices

1. **Keep API keys secret** — Never commit them to the repo
2. **Use GitHub Secrets** — Always store credentials as secrets
3. **Limit token permissions** — GITHUB_TOKEN is automatically scoped
4. **Audit logs** — Check Actions logs periodically for anomalies
5. **Protect main branch** — Require reviews before merging (optional)

---

## Related Documentation

- [README.md](../README.md) — System overview
- [docs/AGENTS.md](AGENTS.md) — Agent details
- [docs/SETUP.md](SETUP.md) — Local setup
- [scripts/research_agent.py](../scripts/research_agent.py) — Script implementation

---

## Support

If the workflow fails:

1. **Check the logs** — Most errors are self-explanatory
2. **Verify API keys** — Ensure secrets are set correctly
3. **Test locally** — Run scripts manually to isolate issues
4. **Check external services** — Anthropic API, GitHub status
5. **Review script changes** — Ensure scripts in `scripts/` are valid Python

---

**Last updated:** July 8, 2026
