# Cardo Competitive Intelligence Dashboard

A comprehensive competitive intelligence system that tracks motorcycle intercom products and strategic positioning across Cardo, Sena, ASMAX, and Reso. Built with Claude AI agents, Python, and a self-contained HTML dashboard.

**Live at:** https://itcardo.github.io/cardo-intel/ — **migration in progress:** this dashboard is moving to Azure Static Web Apps behind Entra ID login (only `cardosystems.com` accounts), replacing public GitHub Pages hosting. See `AUTOMATION_SETUP.md` → "Step 2: Move hosting to Azure Static Web Apps" for the one-time setup and current status. Until that migration's final step (disabling the GitHub Pages source), the URL above still serves the dashboard with no login required.

**Adding a new brand/site to track:** add an entry to `research/brands.json`, create an empty `research/<slug>.json`, and (optionally) list its ASINs in `research/keepa_asins.json` for Amazon pricing. Nothing else needs to change — `build.py`, the research agents, and the GitHub Actions workflow all read the brand list from that config file.

## What This System Does

This is an **automated competitive research platform** that:

1. **Collects intelligence** from product sites, press coverage, social media, and customer forums across 4 motorcycle communicator brands
2. **Synthesizes insights** using AI agents to identify product gaps, market opportunities, and strategic threats
3. **Renders a dashboard** as a single self-contained HTML file with 10+ interactive tabs analyzing products, pricing, battles, firmware, customer feedback, and strategic recommendations
4. **Publishes daily** to GitHub Pages, updating automatically when new competitive moves are detected

## Architecture Overview

### Three-Layer System

```
┌─────────────────────────────────────────────────────────────┐
│ DASHBOARD LAYER (1 file)                                    │
│ dashboard.html (generated) — self-contained, no runtime deps│
│ • 10 interactive tabs (Overview, Products, Battles, etc.)   │
│ • Renders to GitHub Pages automatically                     │
└─────────────────────────────────────────────────────────────┘
         ↑ (fed by build.py)
┌─────────────────────────────────────────────────────────────┐
│ BUILD LAYER (1 Python script)                               │
│ build.py — embeds JSON data into HTML template              │
│ • Reads 6 research JSON files                               │
│ • Embeds data into dashboard_template.html                  │
│ • Writes dashboard.html + index.html for GitHub Pages       │
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
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Research agents** (run weekly via GitHub Actions, or on-demand) gather competitive intelligence
2. JSON research files are updated with new findings
3. **build.py** reads all 6 research JSON files
4. **build.py** embeds data into an HTML template as a JavaScript variable
5. The rendered **dashboard.html** is a self-contained file (works from file://, no server needed)
6. **Git + GitHub Pages** automatically publishes the dashboard to the web

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

The system runs on a GitHub Actions schedule (Mondays at 14:00 UTC, plus a manual "Run workflow" button) — see `.github/workflows/daily-refresh.yml`:

1. **determine-brands**: reads `research/brands.json` and builds the list of brands the next job runs against, so adding a new competitor is a config change, never a workflow edit.

2. **research-agents** (one parallel job per brand): each calls Claude with its own server-side web search tool to refresh that brand's product specs, pricing, and recent news from its official site and press coverage. Writes `research/{brand}.json`.

3. **social-listeners**: two scripts run in sequence —
   - `social_media_listener.py` collects real public Reddit posts (r/motorcyclegear) via Claude's web search.
   - `apify_social_listener.py` scrapes real Facebook Group and Instagram posts via Apify actors, then has Claude classify (never invent) sentiment/topic/product for each real post.
   - Both append to `customer_feedback[]` (and Instagram posts to `social_media.recent_posts[]`) in each brand JSON.

4. **publish**: runs after research and social listening complete —
   - **Product Expert** (`product_expert.py`) reads all research files and regenerates `product_insights.json` from scratch (analyst brief, executive summary, market pulse, gaps, recommendations, watchlist).
   - **build.py** embeds all research JSON into the HTML template, validates the resulting JavaScript, and writes `dashboard.html` + `index.html`.
   - Commits and pushes the changes to `main` if anything changed; GitHub Pages then rebuilds and publishes automatically.

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
│   └── daily-refresh.yml            # The weekly GitHub Actions workflow
│
├── build.py                         # Build dashboard from JSONs
├── dashboard_template.html          # HTML template with embedded JS
├── dashboard.html                   # (generated) Final deployed dashboard
├── index.html                       # (generated) Same as dashboard.html for GitHub Pages
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
│   └── product_insights.json        # Strategic analysis & recommendations
│
└── .gitignore
```

## Dependencies

- **Python 3.8+** (for build.py and all research scripts)
- **`anthropic` Python package** (`pip install anthropic`) — the research agents call the Claude API directly, using Claude's own server-side web search tool for browsing (no Firecrawl or other scraping CLI involved)
- **`keepa` Python package** (only if Amazon pricing via Keepa is configured — optional, gracefully skipped otherwise)
- **Node.js** (optional, for `node -c` syntax checking during build)

No npm packages, no server, no database, no `gh` CLI — the dashboard is a single self-contained HTML file, and publishing is a plain `git push` to `main` that GitHub Pages picks up automatically. Everything runs inside GitHub Actions' own runners; nothing needs to be installed locally except to develop or test scripts by hand.

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
# Automatic: runs every Monday at 14:00 UTC via GitHub Actions
# (see .github/workflows/daily-refresh.yml)

# On demand: GitHub repo → Actions tab → "Weekly Competitive Research Refresh"
# → "Run workflow"
```

## GitHub Deployment

The dashboard is deployed to GitHub Pages automatically when code is pushed to `main`:

1. Repository: https://github.com/ITCardo/cardo-intel
2. Public URL: https://itcardo.github.io/cardo-intel/
3. Branch: `main` (GitHub Pages builds from root path)
4. Built file: `dashboard.html` (renamed to `index.html` as well for serving)

## Key Design Decisions

1. **Single HTML file output** — No server, no build process at view time. Works from file://, CDN, GitHub Pages, or embedded in email.

2. **JSON-driven** — All data is embedded in the HTML as a single JS variable. Easy to version-control, easy to edit, easy to backup.

3. **AI agents for research** — Claude AI agents gather and synthesize data, reducing manual work while maintaining accuracy through verification.

4. **Weekly refresh** — GitHub Actions keeps competitive intelligence current without manual intervention.

5. **Emphasis on evidence** — Gaps, recommendations, and insights are grounded in real product specs, customer feedback, and press coverage. No speculation.

## Limitations & Future Work

- Facebook Group and Instagram data comes via Apify's hosted scraping actors (`scripts/apify_social_listener.py`), which can still miss member-gated groups or brands with a thin Instagram presence; Reddit is covered separately via Claude's web search
- Tier-1 press coverage for ASMAX and Reso is minimal (mostly regional outlets)
- Some Chinese brand websites are paywalled or behind Great Firewall
- Future: automatic price tracking, warranty claim analysis, retail distribution monitoring

## Contributing

When updating research data:
- Preserve the exact JSON schema — only add/update values, never rename/remove keys
- Use straight ASCII quotes (never typographic "smart" quotes)
- Format all dates as `YYYY-MM-DD`
- Every URL must be real and verifiable
- Validate JSON before committing: `python3 -c "import json; json.load(open('research/cardo.json'))"`

---

**Last updated:** September 28, 2026 | **Repository:** https://github.com/ITCardo/cardo-intel
