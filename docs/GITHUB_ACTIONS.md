# GitHub Actions Setup Guide

This guide covers the automated weekly runs using GitHub Actions.

## Overview

The GitHub Actions workflow (`.github/workflows/daily-refresh.yml` — the filename is a leftover from an earlier daily schedule; the workflow itself is named "Weekly Competitive Research Refresh") automatically:

1. **Runs weekly, Mondays at 14:00 UTC** (adjustable via cron schedule), plus a manual "Run workflow" button
2. **Reads the brand list** from `research/brands.json` (currently cardo, sena, asmax, reso — config-driven, no workflow edit needed to add one)
3. **Runs a research agent per brand, in parallel**, calling the Anthropic API directly (via the `anthropic` Python package) with Claude's `web_search` tool — plus the Keepa API for Amazon pricing
4. **Runs two social listener scripts** — Reddit (via web search) and Facebook Groups/Instagram (via Apify)
5. **Synthesizes strategic insights**, builds the dashboard, and pushes to `main`
6. **Deploys to Azure Static Web Apps** automatically (behind Entra ID login, restricted to assigned Cardo Systems accounts)

All logs are visible in the Actions tab. The four jobs run in sequence (`determine-brands` → `research-agents` → `social-listeners` → `publish`), with `research-agents` fanning out one job per brand.

---

## Prerequisites

1. **GitHub account** with repository access (public or private)
2. **Anthropic API key** (Claude API access) — required
3. **Keepa API key** — optional, only needed for Amazon pricing/rank data
4. **Apify API token** — required as the code currently stands (see Step 1 and the Troubleshooting section)

There is no Firecrawl key — Firecrawl isn't used anywhere in this pipeline.

---

## Step 1: Add GitHub Secrets

GitHub Actions requires API keys to be stored as encrypted secrets.

### 1a. Get your API keys

**Anthropic API Key:**
- Go to https://console.anthropic.com → Settings → API Keys

**Keepa API Key (optional):**
- Go to https://keepa.com → account settings → API

**Apify API Token:**
- Go to https://console.apify.com → Settings → Integrations

### 1b. Add secrets to GitHub

1. Go to `https://github.com/ITCardo/cardo-intel/settings/secrets/actions`
2. Click **"New repository secret"**
3. Add each of:

```
Name: ANTHROPIC_API_KEY
Value: sk-ant-...your-key...
```
```
Name: KEEPA_API_KEY
Value: ...your-key...
```
```
Name: APIFY_API_TOKEN
Value: ...your-token...
```

`ANTHROPIC_API_KEY` is required for every job. `KEEPA_API_KEY` is genuinely optional — if it's unset, the Amazon pricing panel is simply left empty and everything else still works. `APIFY_API_TOKEN` is **not** optional as `scripts/apify_social_listener.py` is currently written — see Troubleshooting.

---

## Step 2: Verify Workflow File

The workflow file is at: `.github/workflows/daily-refresh.yml`

Key configuration:
```yaml
on:
  schedule:
    - cron: '0 14 * * 1'   # Mondays 14:00 UTC
  workflow_dispatch:        # Manual trigger also available
```

### Cron Schedule Examples

| Schedule | Cron |
|----------|------|
| Weekly, Mondays 14:00 UTC (current) | `0 14 * * 1` |
| Weekly, Fridays 09:00 UTC | `0 9 * * 5` |
| Daily 09:00 UTC | `0 9 * * *` |
| Weekdays 09:00 UTC | `0 9 * * 1-5` |

To change the schedule, edit the `cron:` line in `.github/workflows/daily-refresh.yml`.

---

## Step 3: What the Jobs Actually Run

### Job 1: `determine-brands`
Reads `research/brands.json` and outputs the list of brand slugs for the next job's matrix. This is the mechanism that makes adding a competitor a config-only change — see the README's "Adding a new brand" section.

### Job 2: `research-agents` (matrix — one run per brand, in parallel)
```bash
python scripts/research_agent.py cardo
python scripts/research_agent.py sena
python scripts/research_agent.py asmax
python scripts/research_agent.py reso
```
- Runtime: ~2-3 minutes per brand, all running concurrently
- Each run updates `research/<slug>.json` in place and uploads it as a build artifact (jobs in this pipeline don't share a filesystem, so files move between jobs as GitHub Actions artifacts)

### Job 3: `social-listeners`
Downloads and merges the updated brand files from Job 2, then runs:
```bash
python scripts/social_media_listener.py     # Reddit, ~3-4 minutes
python scripts/apify_social_listener.py     # Facebook Groups + Instagram, ~3-5 minutes
```
Both append real posts to each brand's `customer_feedback[]`.

### Job 4: `publish`
Downloads the merged research directory, then:
```bash
python scripts/product_expert.py    # regenerates product_insights.json, ~2-4 minutes
python build.py                     # renders dashboard.html + index.html
python scripts/validate_dashboard_js.py   # sanity-checks the embedded JS
git add research/*.json dashboard.html index.html
git commit -m "Weekly data refresh $(date +%Y-%m-%d)"
git push origin HEAD:main
```
Then, still in `publish`, the "Prepare Azure site folder" and "Deploy to Azure Static Web Apps" steps stage `index.html`, `dashboard.html`, `login.html`, and `staticwebapp.config.json` into `site/` and deploy it via `Azure/static-web-apps-deploy`, publishing the new build to `https://cardo-intel.cardosystems.com/`. This is the only deploy target — GitHub Pages is disabled (see `AUTOMATION_SETUP.md` → Step 2.9), so the push to `main` no longer publishes anything at `itcardo.github.io/cardo-intel`.

---

## Step 4: Monitor and Verify

### View Workflow Runs

1. Go to `https://github.com/ITCardo/cardo-intel/actions`
2. Select **"Weekly Competitive Research Refresh"**
3. View the latest run

### Check Logs

Each job/step logs its progress; click into any job for its log. A green checkmark on `publish` is a good sign, but it can still mean thin results if a step found nothing new that week — sign in at https://cardo-intel.cardosystems.com/ and confirm the "last updated" date, not just the checkmark.

### If a Run Fails

1. **API Key Issues** — verify secrets are set correctly in repo Settings; ensure the Anthropic key has available credit
2. **`APIFY_API_TOKEN` missing** — this specifically fails `social-listeners` and blocks `publish` too (see Troubleshooting)
3. **JSON Parsing Errors** — a Claude response may have been malformed; check the failing job's log, fix the JSON manually if needed, re-run
4. **Git Push Failures** — usually a branch protection rule on `main`; the `publish` job needs `contents: write` permission (already set in the workflow) and push access

---

## Step 5: Manual Trigger

To run the workflow without waiting for the schedule:

1. Go to the **Actions** tab
2. Select **"Weekly Competitive Research Refresh"**
3. Click **"Run workflow"**, choose branch `main`, click **"Run workflow"**

---

## Customization

### Change the schedule
```yaml
on:
  schedule:
    - cron: '0 9 * * 5'  # e.g., Fridays 9 AM UTC instead of Mondays 2 PM UTC
```

### Add a competitor
Add an entry to `research/brands.json` and create an empty `research/<slug>.json`. No workflow edit needed — `determine-brands` reads that file dynamically and the `research-agents` matrix picks up the new slug automatically. See the README's "Adding a new brand" section for the full steps.

### Skip a brand temporarily
Remove (or comment out) its entry in `research/brands.json` rather than editing the workflow — the matrix is generated from that file.

### Add Notifications
```yaml
      - name: Notify Slack on failure
        if: failure()
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"Cardo weekly refresh failed"}' \
            ${{ secrets.SLACK_WEBHOOK }}
```
Add `SLACK_WEBHOOK` as a GitHub secret, and add this step to the existing `notify-failure` job.

---

## Troubleshooting

### Workflow doesn't run on schedule
**Cause:** GitHub disables scheduled workflows on repos with no commits in the past 60 days
**Fix:** Make sure there's activity in the repo; a manual push or run resets the clock

### "API key not found" / authentication error in logs
**Fix:**
1. Go to Settings → Secrets and variables → Actions
2. Verify `ANTHROPIC_API_KEY` (and `KEEPA_API_KEY`, `APIFY_API_TOKEN` if in use) are present
3. Re-run the workflow

### `social-listeners` fails with "APIFY_API_TOKEN not set - skipping (this is a hard requirement, not optional)"
**Cause:** `scripts/apify_social_listener.py` deliberately exits with an error if the token is missing — it does not degrade gracefully
**Impact:** Because `publish` depends on `social-listeners`, this blocks that week's entire site update, not just the Facebook/Instagram data — even though research and Keepa pricing succeeded
**Fix:** Add the `APIFY_API_TOKEN` secret (Step 1). Making this genuinely optional would be a small code change to `apify_social_listener.py` (catch the missing token and skip instead of `sys.exit(1)`), not a config change.

### JSON validation errors
**Cause:** Claude API returned malformed JSON or a network issue mid-run
**Fix:** Check the full log for details; fix the JSON manually if needed; re-run the workflow

### Changes not pushed to GitHub
**Expected:** The `publish` job checks for changes first and skips the commit if nothing changed that week — check the "Check for changes" step's log, which prints "No changes detected" in that case

### Dashboard not updating
**Fix:**
1. Hard refresh browser: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
2. Confirm the "Deploy to Azure Static Web Apps" step in `publish` actually ran (not the "skip" no-op) and succeeded
3. Verify the commit was pushed: `git log -1` in a local clone should show that week's refresh commit

---

## Cost Considerations

### Anthropic API Usage

Each weekly run calls Claude for:
- **4 research agents** (one per brand, running in parallel)
- **1 Reddit social listener** (capped at 8 web searches)
- **1 Apify social listener** (classification only, no web search)
- **1 Product Expert synthesis** (no web search — pure analysis over already-gathered data)

At current pricing (Sonnet 5.5: $2/$10 per million input/output tokens; web search: $10 per 1,000 searches), this pipeline runs to realistically low single-digit dollars per week at its current volume (weekly cadence, capped output per call). See `AUTOMATION_SETUP.md` for the full cost picture including Keepa and Apify.

### GitHub Actions

Free for public repositories; private repos get 2,000 free minutes/month. Each weekly run takes roughly 15-20 minutes total across all jobs — well within the free tier either way.

---

## Security Best Practices

1. **Keep API keys secret** — Never commit them to the repo
2. **Use GitHub Secrets** — Always store credentials as secrets
3. **Limit token permissions** — the workflow's built-in `GITHUB_TOKEN` is not used for pushing; `publish` uses the repo's own git credentials with `contents: write` permission, scoped to this workflow run only
4. **Audit logs** — Check Actions logs periodically for anomalies
5. **Protect main branch** — Require reviews before merging (optional, but note it will interact with the `publish` job's direct push to `main`)

---

## Related Documentation

- [README.md](../README.md) — System overview
- [docs/AGENTS.md](AGENTS.md) — Script details
- [docs/SETUP.md](SETUP.md) — Local setup
- [scripts/research_agent.py](../scripts/research_agent.py) — Script implementation
- [.github/workflows/daily-refresh.yml](../.github/workflows/daily-refresh.yml) — The workflow itself

---

## Support

If the workflow fails:

1. **Check the logs** — most errors are self-explanatory
2. **Verify API keys** — ensure all required secrets are set correctly
3. **Test locally** — run scripts manually to isolate issues (see `docs/SETUP.md`)
4. **Check external services** — Anthropic, Keepa, and Apify status pages
5. **Review script changes** — ensure scripts in `scripts/` are valid Python

---

**Last updated:** September 30, 2026
