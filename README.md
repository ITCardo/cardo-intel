# Cardo Competitive Intelligence Dashboard

A comprehensive competitive intelligence system that tracks motorcycle intercom products and strategic positioning across Cardo, Sena, ASMAX, and Reso. Built with Claude AI agents, Python, and a self-contained HTML dashboard. A second, independent watch tracks the brands' patent filings (IP & Patents, see below).

**Live at:** https://cardo-intel.cardosystems.com/ — hosted on Azure Static Web Apps behind Microsoft/Entra ID sign-in, restricted to assigned Cardo Systems accounts only. The old public URL (`itcardo.github.io/cardo-intel`) is gone: GitHub Pages is disabled and the `CNAME` file removed, so it no longer serves or redirects anywhere. See `AUTOMATION_SETUP.md` → "Step 2" for full setup details.

**Adding a new brand/site to track:** add an entry to `research/brands.json`, create an empty `research/<slug>.json`, and (optionally) list its ASINs in `research/keepa_asins.json` for Amazon pricing. Nothing else needs to change — `build.py`, the research agents, and the GitHub Actions workflow all read the brand list from that config file.

## What This System Does

This is an **automated competitive research platform** that:

1. **Collects intelligence** from product sites, press coverage, social media, and customer forums across 4 motorcycle communicator brands
2. **Synthesizes insights** using AI agents to identify product gaps, market opportunities, and strategic threats
3. **Watches patents (IP)** for all four brands from the European Patent Office (EPO) and Google's public patent dataset, files each patent into one of Cardo's own product families, and flags what is new or changed since the previous week
4. **Renders a dashboard** as a single self-contained HTML file with 10+ interactive tabs analyzing products, pricing, battles, firmware, customer feedback, and strategic recommendations
5. **Publishes weekly** to the login-gated dashboard, updating automatically when new competitive moves are detected

## Architecture Overview

### Three-Layer System

```
┌─────────────────────────────────────────────────────────────┐
│ DASHBOARD LAYER (1 file)                                    │
│ dashboard.html (generated) — self-contained, no runtime deps│
│ • 10 interactive tabs (Overview, Products, Battles, etc.)   │
│ • Deployed to Azure Static Web Apps, behind Entra ID login   │
└─────────────────────────────────────────────────────────────┘
         ↑ (fed by build.py)
┌─────────────────────────────────────────────────────────────┐
│ BUILD LAYER (1 Python script)                               │
│ build.py — embeds JSON data into HTML template              │
│ • Reads the research JSON files (incl. ip_results.json)     │
│ • Embeds data into dashboard_template.html                  │
│ • Writes dashboard.html + index.html for deployment         │
└─────────────────────────────────────────────────────────────┘
         ↑ (fed by agents)
┌─────────────────────────────────────────────────────────────┐
│ RESEARCH LAYER (Research data in JSON)                      │
│                                                              │
│ Brand Research Files (refreshed weekly, per research/brands.json): │
│ • research/cardo.json      (products, news, social, etc.)  │
│ • research/sena.json                                        │
│ • research/asmax.json                                       │
│ • research/reso.json                                        │
│                                                              │
│ Derived Analysis (updated by Product Expert agent):         │
│ • research/gap_analysis.json   (pricing/feature gaps)       │
│ • research/battles.json        (head-to-head comparisons)   │
│ • research/product_insights.json (strategic analysis)       │
│                                                              │
│ IP & Patents (written by the IP crawler, Saturdays):        │
│ • research/ip_results.json     (patent records per brand)   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Research agents** (run weekly via GitHub Actions, or on-demand) gather competitive intelligence
2. JSON research files are updated with new findings
3. **build.py** reads all research JSON files, including `research/ip_results.json` (written by the IP crawler on Saturday) if it exists
4. **build.py** embeds data into an HTML template as a JavaScript variable (the patent data sits under `DATA.ip`)
5. The rendered **dashboard.html** is a self-contained file (works from file://, no server needed)
6. **Git push** triggers the `publish` job's Azure Static Web Apps deploy step, publishing the dashboard behind Entra ID login

## Dashboard Tabs

| Tab | Purpose | Data Source |
|-----|---------|-------------|
| **Overview** | Brand positioning matrix, company info, product counts | 4 brand JSONs |
| **Products** | Sortable/filterable product table with specs | 4 brand JSONs |
| **Battles** | Head-to-head comparisons, 16-dimension rating matrices | battles.json |
| **Model Compare** | Detailed side-by-side specs of selected products | 4 brand JSONs |
| **Pricing** | Scatter plot of price vs features (mesh, warranty, etc.) | 4 brand JSONs |
| **Gap Analysis** | Cardo's competitive gaps with evidence and benchmarks | gap_analysis.json |
| **Social & Press** | Recent news, press reviews, social media posts | 4 brand JSONs |
| **Software & Firmware** | App versions, firmware updates, release notes | 4 brand JSONs |
| **Voice of the Customer** | Real customer feedback from Reddit and Facebook | 4 brand JSONs |
| **Product Insights** | Strategic analysis, market pulse, recommendations | product_insights.json |
| **IP & Patents** | Patent records per brand, product family, status, new/changed this week | ip_results.json |

The patent data is embedded in every build (`DATA.ip`, with per-brand counts of total, new, changed, pending, granted and expired) and shown in two places in the dashboard: the **IP & Patents** tab (last item in the sidebar, shortcut `6`) and a **Patents and designs · weekly check** strip on the Brief page with the new/changed count per brand. The tab has filters for brand, status, type and product family, a search that ignores spaces in patent numbers, links to Google Patents and Espacenet, and lists new or changed records first. It follows the sidebar brand filter. If `research/ip_results.json` is missing or only demo data, the tab and the strip are hidden. The standalone page is still available as a backup: download the artifact `ip-preview` from the latest **IP Crawler Weekly** run and open `ip_preview.html`.

## Research Data Schema

Each brand JSON (`cardo.json`, `sena.json`, etc.) contains:

```json
{
  "competitor": "Cardo",
  "website": "https://...",
  "company": { "founded": 2003, "hq": "Israel", ... },
  "products": [
    {
      "name": "Packtalk Pro",
      "tier": "flagship",
      "category": "communicator",
      "msrp_usd": 499.95,
      "street_price_usd": 449.95,
      "intercom_tech": "DMC Gen2 mesh (31 riders)",
      "range_km": 1.6,
      "max_riders": 31,
      "audio": "Sound by JBL 40mm speaker",
      "talk_time_hours": 13,
      "waterproof": "IP67",
      "features": ["Crash detection", "SOS", "Auto-pairing"],
      "release_year": 2023,
      "dimensions": { "form_factor": "...", "ease_of_use": "...", ... },
      "notes": "..."
    }
  ],
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "recent_news": [
    { "date": "2026-07-01", "headline": "...", "source": "...", "url": "..." }
  ],
  "social_media": {
    "instagram": { "url": "https://instagram.com/...", "followers": 45000 },
    "facebook": { "url": "https://facebook.com/...", "followers": 32000 },
    "youtube": { "url": "https://youtube.com/...", "subscribers": 18000 },
    "recent_posts": [
      { "date": "2026-07-05", "platform": "Instagram", "summary": "...", "url": "..." }
    ]
  },
  "press_coverage": {
    "overall_tone": "positive",
    "reviews": [
      { "outlet": "MCN", "product": "60X", "date": "2026-07-02", "rating": "4/5", "url": "..." }
    ]
  },
  "firmware_updates": [
    { "date": "2026-07-02", "product": "60X", "type": "firmware", "version": "3.1", "title": "...", "changes": [...], "url": "...", "source": "..." }
  ],
  "current_software": {
    "app_name": "Sena app",
    "app_ios_version": "8.2.1",
    "app_android_version": "8.2.0",
    "app_last_updated": "2026-06-28"
  },
  "product_firmware": [
    { "product": "60X", "firmware_version": "3.1", "firmware_last_updated": "2026-07-02", "release_notes_url": "...", "user_manual_url": "...", "support_url": "..." }
  ],
  "customer_feedback": [
    { "date": "2026-07-08", "source": "Reddit", "forum": "r/motorcyclegear", "product": "Packtalk Pro", "sentiment": "negative", "topic": "Pairing issues", "summary": "...", "url": "..." }
  ],
  "sources": ["https://...", "..."]
}
```

## Weekly Refresh Workflow

The refresh runs every **Monday at 07:00 UTC**, started by the Azure Logic App `logic-cardo-intel-trigger` (see [How the workflows are started](#how-the-workflows-are-started)), or on demand with the "Run workflow" button — see `.github/workflows/daily-refresh.yml`. The workflow has no `schedule:` trigger of its own: GitHub's built-in scheduler proved unreliable for this repo, so the Logic App calls the workflow through the GitHub API instead.

1. **determine-brands**: reads `research/brands.json` and builds the list of brands the next job runs against, so adding a new competitor is a config change, never a workflow edit.

2. **research-agents** (one parallel job per brand): each calls Claude with its own server-side web search tool to refresh that brand's product specs, pricing, and recent news from its official site and press coverage. Writes `research/{brand}.json`.

3. **social-listeners**: two scripts run in sequence —
   - `social_media_listener.py` collects real public Reddit posts (r/motorcyclegear) via Claude's web search.
   - `apify_social_listener.py` scrapes real Facebook Group and Instagram posts via Apify actors, then has Claude classify (never invent) sentiment/topic/product for each real post.
   - Both append to `customer_feedback[]` (and Instagram posts to `social_media.recent_posts[]`) in each brand JSON.

4. **publish**: runs after research and social listening complete —
   - **Product Expert** (`product_expert.py`) reads all research files and regenerates `product_insights.json` from scratch (analyst brief, executive summary, market pulse, gaps, recommendations, watchlist).
   - **build.py** embeds all research JSON into the HTML template, validates the resulting JavaScript, and writes `dashboard.html` + `index.html`.
   - Commits and pushes the changes to `main` if anything changed, then deploys the built files to Azure Static Web Apps (behind Entra ID login).

## IP & Patent Crawler

A separate weekly job, **IP Crawler Weekly** (`.github/workflows/ip-crawler.yml`, code in `ip-preview/`), tracks the patent filings of Sena, Cardo, Reso and ASMAX. It is independent of the Monday refresh so that a failure in one never blocks the other.

**Schedule:** Saturday 03:17 UTC, started by the Logic App `logic-cardo-intel-ip-trigger`. Saturday night because the EPO asks automatic tools to run between 19:00 and 07:00 GMT or at weekends. It can also be started by hand (Actions → "IP Crawler Weekly" → Run workflow; the `demo` option shows invented records and changes nothing).

**Sources**
- **EPO Open Patent Services** (official API): searches by applicant name, looks up numbers, fetches patent families and legal events (lapse, withdrawal, refusal).
- **Google BigQuery** public patent dataset (official, optional): a second, independent source; every row shows which sources saw it.
- Google Patents and Espacenet are **links only**: Google's site is closed to automated access, so it is not scraped.

**What it produces:** `research/ip_results.json`, committed to `main` by the workflow after a complete run. It holds, per brand, every patent record (number, kind, title, jurisdiction, filing and priority dates, status, product family, sources, flags). The Monday build embeds this file; the previous Saturday's file is also what the next crawl compares against to detect **NEW** and **CHANGED** records.

**How to read the results**
- **Status** comes from EPO legal events when there is one, otherwise it is estimated from the kind code and the legal term (marked "est."). Lapses in only some countries and office actions (for example a JP "notification of reasons for refusal") do not make a patent expired; they show as a grey note under the status.
- **Product family** is Cardo's own grouping of the patents by subject (not the patent family number). New patents go into an existing family when Claude finds one that fits, otherwise Claude creates the next numbered family and lists it in a banner for review. Corrections go in `ip-preview/config.json` (`family_overrides`).
- **NEW / CHANGED:** a number not seen in the previous run, or a status that moved forward (Pending → Granted → Expired). The brand-name list and the review list of near-matches are in `ip-preview/config.json`.

**Safety rules built in:** runs started with `demo`, or with a brand filter, never overwrite `research/ip_results.json`; an incomplete run (an EPO block or an error) leaves the previous file in place; the build skips the IP data if the file is missing, invalid or a demo, so the rest of the dashboard is never affected.

Details, limits and the configuration file are documented in `ip-preview/README.md`.

## How the workflows are started

Both workflows have only a `workflow_dispatch` trigger. Two Azure Logic Apps (Consumption plan, one per workflow) call the GitHub API on a weekly timer:

| Logic App | Starts | When (UTC) |
|-----------|--------|------------|
| `logic-cardo-intel-trigger` | `daily-refresh.yml` (research, build, Azure deploy) | Mondays 07:00 |
| `logic-cardo-intel-ip-trigger` | `ip-crawler.yml` (patent watch) | Saturdays 03:17 |

Each Logic App is a Recurrence trigger plus one HTTP action:

```
POST https://api.github.com/repos/ITCardo/cardo-intel/actions/workflows/<workflow file>/dispatches
Authorization: Bearer <fine-grained token>      body: {"ref":"main"}
```

- **Token:** a GitHub fine-grained personal access token, resource owner `ITCardo`, repository `cardo-intel` only, permission **Actions: Read and write**, 1-year expiry. It is stored in the HTTP action's header (Secure inputs on) and is visible to anyone with Contributor access on the Logic App, so keep that resource group restricted. **Renew it before it expires** (put a calendar reminder 2 weeks ahead): generate a new token, paste it in the Logic App's code view in both Logic Apps, then delete the old one.
- **Alerts:** each Logic App has an Azure Monitor alert rule on "Runs Failed" that emails the owner, which is how an expired or invalid token shows up. A failed *GitHub* run is not covered by this alert: check the Actions tab if the dashboard looks stale.
- **Changing the schedule:** edit the Recurrence trigger in the Logic App (designer or code view), not the workflow file. Times are UTC and do not follow daylight saving.
- **Why not a cron in the workflow:** a `schedule:` trigger in the workflow files did not fire reliably for this repo (one test run in several hours), so it was removed to avoid duplicate runs.

## Secrets and variables

Repository → Settings → Secrets and variables → Actions.

| Name | Type | Used by | Purpose |
|------|------|---------|---------|
| `ANTHROPIC_API_KEY` | secret | research agents, Product Expert, social listeners, IP crawler | Claude API (needs credits; the IP crawler uses it only to file new patents into product families) |
| `KEEPA_API_KEY` | secret (optional) | research agents | Amazon pricing |
| `APIFY_API_TOKEN` | secret | Apify social listener | Facebook Groups and Instagram |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | secret | publish job | Deploys the site to Azure Static Web Apps |
| `EPO_OPS_KEY`, `EPO_OPS_SECRET` | secrets | IP crawler | EPO Open Patent Services consumer key and secret |
| `GCP_SA_KEY` | secret (optional) | IP crawler | Service-account JSON key, role BigQuery Job User |
| `GCP_PROJECT` | variable (optional) | IP crawler | Google Cloud project id for BigQuery |
| `BQ_MAX_GB` | variable (optional) | IP crawler | Refuse any BigQuery query that would scan more than this (default 300) |

The GitHub token used by the Logic Apps is not a repository secret: it lives only in the Logic Apps.

## Files & Directories

```
cardo-intel/
├── README.md                         # This file
├── AUTOMATION_SETUP.md               # GitHub Actions secrets/setup reference
├── docs/
│   ├── AGENTS.md                    # Detailed agent descriptions
│   ├── SETUP.md                     # Installation & local setup
│   ├── GITHUB_ACTIONS.md            # Workflow reference
│   └── DATA_SCHEMA.md               # JSON schema reference
│
├── .github/workflows/
│   ├── daily-refresh.yml            # Weekly refresh (Mondays, started by Azure Logic App)
│   └── ip-crawler.yml               # Weekly IP crawler (Saturdays, started by Azure Logic App)
│
├── build.py                         # Build dashboard from JSONs
├── dashboard_template.html          # HTML template with embedded JS
├── dashboard.html                   # (generated) Final deployed dashboard
├── index.html                       # (generated) Same as dashboard.html, deployed alongside it
│
├── scripts/
│   ├── research_agent.py            # Per-brand research (Claude + web search)
│   ├── social_media_listener.py     # Reddit customer feedback (Claude + web search)
│   ├── apify_social_listener.py     # Facebook Group + Instagram scraping (Apify) + Claude classification
│   └── product_expert.py            # Regenerates product_insights.json
│
├── research/
│   ├── brands.json                  # Brand/site config — add a competitor here, nothing else
│   ├── cardo.json                   # Brand research data
│   ├── sena.json
│   ├── asmax.json
│   ├── reso.json
│   ├── gap_analysis.json            # Pricing & feature gap analysis
│   ├── battles.json                 # Head-to-head comparisons (16 dimensions)
│   ├── product_insights.json        # Strategic analysis & recommendations
│   └── ip_results.json              # Patent records, written by ip-crawler.yml
│
├── ip-preview/                      # IP crawler code, config.json (names, product families), tests
│   └── README.md                    # IP crawler details and limits
│
└── .gitignore
```

## Dependencies

- **Python 3.8+** (for build.py and all research scripts)
- **`anthropic` Python package** (`pip install anthropic`) — the research agents call the Claude API directly, using Claude's own server-side web search tool for browsing (no Firecrawl or other scraping CLI involved)
- **`keepa` Python package** (only if Amazon pricing via Keepa is configured — optional, gracefully skipped otherwise)
- **Node.js** (optional, for `node -c` syntax checking during build)
- IP crawler only (installed by its workflow): `requests`, `anthropic`, `google-cloud-bigquery`, `pytest`

No npm packages, no server, no database, no `gh` CLI — the dashboard is a single self-contained HTML file, and publishing is a plain `git push` to `main` that the `publish` job's Azure Static Web Apps deploy step picks up automatically. Everything runs inside GitHub Actions' own runners; nothing needs to be installed locally except to develop or test scripts by hand.

## Quick Start

### To run locally:
```bash
# Edit research/*.json files with new data
python3 build.py
# → outputs dashboard.html (works in any browser, no server needed)
```

### To view the dashboard:
```bash
# Option 1: Open in browser directly
open dashboard.html

# Option 2: Run a simple HTTP server (to test with file:// URLs)
python3 -m http.server 8000
# → open http://localhost:8000/dashboard.html
```

### To refresh the research (automatic weekly, or on demand):
```
# Automatic: runs every Monday at 07:00 UTC, started by the Azure Logic App
# "logic-cardo-intel-trigger" (see "How the workflows are started")

# On demand: GitHub repo → Actions tab → "Weekly Competitive Research Refresh"
# → "Run workflow"

# Patent watch on demand: Actions tab → "IP Crawler Weekly" → "Run workflow"
```

## Deployment

The dashboard is deployed to Azure Static Web Apps automatically when code is pushed to `main`:

1. Repository: https://github.com/ITCardo/cardo-intel
2. Live URL: https://cardo-intel.cardosystems.com/ (login required — Entra ID, restricted to assigned Cardo Systems accounts)
3. Source: the `publish` job in `.github/workflows/daily-refresh.yml` stages `index.html`, `dashboard.html`, `login.html`, and `staticwebapp.config.json` into a `site/` folder and deploys it via `Azure/static-web-apps-deploy`
4. Built files: `dashboard.html` (renamed to `index.html` as well for serving)
5. Legacy path: `https://itcardo.github.io/cardo-intel/` no longer exists — GitHub Pages is disabled and there is no redirect to the URL above (see `AUTOMATION_SETUP.md` → Step 2.9)

## Key Design Decisions

1. **Single HTML file output** — No server, no build process at view time. Works from file://, CDN, or embedded in email.

2. **JSON-driven** — All data is embedded in the HTML as a single JS variable. Easy to version-control, easy to edit, easy to backup.

3. **AI agents for research** — Claude AI agents gather and synthesize data, reducing manual work while maintaining accuracy through verification.

4. **Weekly refresh** — GitHub Actions keeps competitive intelligence current without manual intervention; an Azure Logic App starts each run on schedule.

5. **Emphasis on evidence** — Gaps, recommendations, and insights are grounded in real product specs, customer feedback, and press coverage. No speculation.

## Limitations & Future Work

- Facebook Group and Instagram data comes via Apify's hosted scraping actors (`scripts/apify_social_listener.py`), which can still miss member-gated groups or brands with a thin Instagram presence; Reddit is covered separately via Claude's web search
- Tier-1 press coverage for ASMAX and Reso is minimal (mostly regional outlets)
- Some Chinese brand websites are paywalled or behind Great Firewall
- Patent status is only as good as the legal events the EPO returns; where there is none it is estimated from the kind code and term and marked "est."
- The EPO has fair-use limits (about 4 GB a week) and asks for automatic runs in the evening or at weekends; the Saturday-night schedule is chosen for this
- Patent applicant names are matched in Latin script; the Chinese-character names of the Shenzhen and Hong Kong companies still need confirmation by a Chinese reader before they are added to `ip-preview/config.json`
- Future: automatic price tracking, warranty claim analysis, retail distribution monitoring

## Contributing

When updating research data:
- Preserve the exact JSON schema — only add/update values, never rename/remove keys
- Use straight ASCII quotes (never typographic "smart" quotes)
- Format all dates as `YYYY-MM-DD`
- Every URL must be real and verifiable
- Validate JSON before committing: `python3 -c "import json; json.load(open('research/cardo.json'))"`

---

**Last updated:** October 12, 2026 | **Repository:** https://github.com/ITCardo/cardo-intel
