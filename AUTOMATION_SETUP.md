# ⚙️ GitHub Actions Automation — Setup Reference

The automated research workflow already lives on `ITCardo/cardo-intel` (`.github/workflows/daily-refresh.yml`). This doc covers what it needs to run, how to verify it's working, and how to change it.

## What's Here

✅ **GitHub Actions Workflow** — `.github/workflows/daily-refresh.yml`
- Runs weekly, Mondays at 14:00 UTC (configurable), plus a manual "Run workflow" button
- Four jobs in sequence: `determine-brands` → `research-agents` (parallel, one per brand) → `social-listeners` → `publish`

✅ **Python Scripts** — `scripts/` directory
- `research_agent.py` — per-brand research, using Claude with its own web search tool (no external scraping service)
- `social_media_listener.py` — Reddit customer feedback, also via Claude's web search
- `apify_social_listener.py` — real Facebook Group and Instagram posts via Apify, classified by Claude
- `product_expert.py` — synthesizes `product_insights.json` from all research

✅ **Config** — `research/brands.json`
- Add a new competitor by adding one entry here; no code or workflow change needed

---

## Step 1: Add Repository Secrets

Go to `https://github.com/ITCardo/cardo-intel/settings/secrets/actions` → **New repository secret** for each of:

| Secret | Required? | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Required** — nothing runs without it | https://console.anthropic.com → Settings → API Keys |
| `KEEPA_API_KEY` | Optional — Amazon pricing/rank panel stays empty if unset, everything else still works | https://keepa.com → account settings → API |
| `APIFY_API_TOKEN` | Required as the code is currently written — `apify_social_listener.py` exits with an error if this is missing, which blocks the `publish` job too (see Troubleshooting) | https://console.apify.com → Settings → Integrations |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | Required once the site is gated behind login (see Step 2) — until this exists, the `publish` job's Azure deploy step just skips itself harmlessly | Azure Portal → your Static Web App resource → Overview → "Manage deployment token" |

There is no Firecrawl key — Firecrawl was replaced by Claude's own server-side web search tool, called directly from the research scripts.

---

## Step 2: Move hosting to Azure Static Web Apps, gated behind Entra ID login

The dashboard used to be public on GitHub Pages. It's now meant to sit behind a Microsoft sign-in restricted to `cardosystems.com` accounts, hosted on Azure Static Web Apps (Standard plan — the Free plan can't restrict login to one tenant). This is a one-time setup:

1. **Create the Static Web App** — Azure Portal → Create a resource → Static Web App → Standard plan. For "Deployment details" choose **Other** (not GitHub) — this avoids Azure auto-generating its own competing workflow file; this repo's own `.github/workflows/daily-refresh.yml` already has the deploy step it needs.
2. **Get the deployment token** — resource → Overview → "Manage deployment token" → add it as the `AZURE_STATIC_WEB_APPS_API_TOKEN` secret (Step 1 above).
3. **Register an Entra app** for this login — Entra admin center → App registrations → New registration. Redirect URI (Web): `https://<your-swa-hostname>.azurestaticapps.net/.auth/login/aad/callback` (shown on the Static Web App's Overview page). Note the Application (client) ID and Directory (tenant) ID, then add a client secret under Certificates & secrets, and grant Microsoft Graph delegated permissions: `email`, `openid`, `profile`, `User.Read`.
4. **Add those as Static Web App application settings** (not GitHub secrets) — resource → Configuration → Application settings: `AZURE_CLIENT_ID` and `AZURE_CLIENT_SECRET`. These names must match `staticwebapp.config.json` at the repo root, which also needs its `<CARDO_ENTRA_TENANT_ID>` placeholder replaced with the real tenant ID from step 3.
5. **(Optional) Entra Company Branding** — Entra admin center → Company branding, if not already set up org-wide. This puts the Cardo logo/colors on the actual Microsoft sign-in screen itself (affects every Microsoft login at Cardo, not just this dashboard). Separately, `login.html` at the repo root is a Cardo-branded landing page shown *before* that Microsoft screen, with a "Sign in with Microsoft" button.
6. **Point the domain at Azure instead of GitHub Pages** — in Cloudflare DNS, change the `cardo-intel` CNAME record from `itcardo.github.io` to the Static Web App's hostname (or add it as a custom domain directly on the Azure resource, which is the cleaner long-term option — Azure will want its own DNS validation record first).
7. **Disable the old public path** — once the Azure-hosted, login-gated site is confirmed working end to end, go to repo → Settings → Pages and set Source to "None." This is what actually stops the dashboard from being reachable without logging in — until this step, `itcardo.github.io/cardo-intel` still serves the dashboard with no login at all.

---

## Step 3: Verify It Works

1. Go to `https://github.com/ITCardo/cardo-intel/actions` → "Weekly Competitive Research Refresh" → **Run workflow**.
2. Watch the jobs run: `determine-brands` → `research-agents` (one per brand, parallel) → `social-listeners` → `publish`. Each shows live status; click into any job for its log.
3. In `publish`, confirm "Deploy to Azure Static Web Apps" actually ran (not the "skipping" no-op step) — that only happens once `AZURE_STATIC_WEB_APPS_API_TOKEN` is set.
4. Open the dashboard's URL in a private/incognito window: you should land on the Cardo-branded `login.html` first, then a Microsoft sign-in screen after clicking through, and only then the actual dashboard — confirm the "last updated" date matches today. A green run can still mean thin results if a step found nothing new, so check the actual content, not just the checkmark.
5. Try (or ask a colleague to try) signing in with a non-Cardo Microsoft account — it should be rejected. This is the actual security property Step 2 exists to provide; skipping this check means you don't actually know it's restricted to your tenant.

---

## Customization

### Change the schedule

Edit `.github/workflows/daily-refresh.yml`:

```yaml
on:
  schedule:
    - cron: '0 14 * * 1'   # Mondays 14:00 UTC — change day/time here
```

Push the change and it takes effect on the next scheduled run.

### Add a competitor

Add an entry to `research/brands.json` (slug, name, website, social handles, Facebook groups, Reddit search terms) and create an empty `research/<slug>.json`. Nothing else needs to change — `build.py`, all four scripts, and the workflow's brand matrix all read from that one file.

---

## Cost

All three services bill pay-as-you-go, not a flat fee:

- **Anthropic API**: the main cost driver — depends on which model the scripts use (`claude-opus-4-8` vs a cheaper Sonnet model) and how much web search runs each week. Realistically low single-digit dollars per week at this pipeline's volume (weekly cadence, capped output per call).
- **Keepa**: token-based subscription, only if enabled.
- **Apify**: usage-based, only if enabled.
- **GitHub Actions**: free (public repo).

---

## Troubleshooting

### Workflow doesn't show in the Actions tab
The workflow file is already on `main` — check you're looking at `ITCardo/cardo-intel`, not the original personal-account repo it was migrated from.

### "API key not found" / authentication error in logs
Add the missing secret (Step 1). Note `ANTHROPIC_API_KEY` is required for every job; `KEEPA_API_KEY` is genuinely optional; `APIFY_API_TOKEN` is *not* optional as the code stands today — `apify_social_listener.py` deliberately exits with an error if it's missing, which fails the `social-listeners` job and, because `publish` depends on it, blocks the whole site update that week even if research and Keepa worked fine.

### Workflow fails with a JSON parse error
Check the failing job's log — usually a Claude response got cut off or malformed. Re-run manually; these are rarely persistent.

### Dashboard not updating after a successful run
Hard-refresh your browser (Cmd+Shift+R) and wait 30–60 seconds for GitHub Pages to finish rebuilding.

### No automatic (scheduled) runs happening
GitHub disables scheduled workflows on repos with no commits in 60 days — as long as the repo stays active, this isn't a concern, but it's the first thing to check if the weekly run silently stops firing.

---

## Documentation

- [docs/GITHUB_ACTIONS.md](docs/GITHUB_ACTIONS.md) — workflow reference
- [README.md](README.md) — system overview
- [docs/AGENTS.md](docs/AGENTS.md) — agent/script descriptions
- [.github/workflows/daily-refresh.yml](.github/workflows/daily-refresh.yml) — the workflow itself
