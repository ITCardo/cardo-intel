# Cardo Competitive Intelligence Dashboard

A comprehensive competitive intelligence system that tracks motorcycle intercom products and strategic positioning across Cardo, Sena, ASMAX, and Reso. Built with Claude AI agents, Python, and a self-contained HTML dashboard.

**Live at:** https://itcardo.github.io/cardo-intel/

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
│ 4 Brand Research Files (refreshed daily by agents):         │
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
│ Helper Scripts (optional, for local research):              │
│ • ig_product_scan.py (scan Instagram for product launches)  │
│ • apify_scan.py (Apify scraper template)                    │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Research agents** (spawned daily or on-demand) gather competitive intelligence
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

## Daily Refresh Workflow

The system runs a daily refresh (7:00 AM local, managed by scheduled task):

1. **4 Research Agents** run in parallel, each updating one brand JSON:
   - Scan official product sites for new launches and pricing
   - Check press coverage (motorcycle magazines, YouTube, blogs)
   - Scan social media (Instagram, YouTube, Reddit, Facebook groups)
   - Look for firmware/app updates
   - Format: `research/{brand}.json`

2. **Social Media Listener Agent** runs in parallel:
   - Collects real customer feedback from forums
   - Appends to `customer_feedback[]` in each brand JSON
   - Sources: Cardo/Sena/ASMAX/Reso owner Facebook groups + r/motorcyclegear

3. **Derived Analysis Update** (manual or auto):
   - Update `battles.json` if new products or major price changes detected
   - Update `gap_analysis.json` for pricing/feature gaps

4. **Product Expert Agent** runs after research completes:
   - Reads ALL research files + battles.json + gap_analysis.json
   - Regenerates `product_insights.json` from scratch with:
     - Analyst brief (strategic take)
     - Executive summary
     - Market pulse (recent competitive moves)
     - Product gaps (evidence-grounded, severity-rated)
     - Strategic recommendations (prioritized by horizon/effort)
     - Watchlist (key signals to monitor)

5. **Dashboard Build** (build.py):
   - Python reads all 6 JSON research files
   - Embeds JSON as a JavaScript variable in the HTML
   - Validates JavaScript syntax
   - Outputs `dashboard.html` and `index.html`

6. **Publish to GitHub**:
   - Git commit with message "Daily data refresh YYYY-MM-DD"
   - Push to `origin/main` (explicit, not bare push)
   - GitHub Pages automatically rebuilds and publishes

## Files & Directories

```
cardo-intel/
├── README.md                         # This file
├── docs/
│   ├── AGENTS.md                    # Detailed agent descriptions
│   ├── SETUP.md                     # Installation & local setup
│   └── DATA_SCHEMA.md               # JSON schema reference
│
├── build.py                         # (5 min) Build dashboard from JSONs
├── dashboard_template.html          # HTML template with embedded JS
├── dashboard.html                   # (generated) Final deployed dashboard
├── index.html                       # (generated) Same as dashboard.html for GitHub Pages
│
├── research/
│   ├── cardo.json                   # Brand research data
│   ├── sena.json
│   ├── asmax.json
│   ├── reso.json
│   ├── gap_analysis.json            # Pricing & feature gap analysis
│   ├── battles.json                 # Head-to-head comparisons (16 dimensions)
│   ├── product_insights.json        # Strategic analysis & recommendations
│   ├── cardo.md, sena.md, ...       # (optional) Notes/references per brand
│
├── ig_product_scan.py               # (optional) Instagram scraper for product launches
├── apify_scan.py                    # (optional) Apify-based scraper template
│
└── .gitignore                       # Ignores .firecrawl/, .ig_session.json, etc.
```

## Dependencies

- **Python 3.8+** (for build.py)
- **Node.js** (optional, for `node -c` syntax checking during build)
- **firecrawl CLI** (for daily research agents to scrape the web)
- **Claude AI SDK / Agent framework** (for spawning research agents)
- **GitHub CLI** (`gh` command) (for publishing to GitHub Pages)

No npm packages, no server, no database — the dashboard is a single self-contained HTML file.

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

### To refresh the research daily (automatic via scheduled task):
```bash
# Manually trigger the daily refresh (normally runs at 7 AM):
# Use the Claude Code CLI or dashboard to invoke the scheduled task
# Or run agents manually (see docs/AGENTS.md for details)
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

4. **Daily refresh** — Scheduled task keeps competitive intelligence current without manual intervention.

5. **Emphasis on evidence** — Gaps, recommendations, and insights are grounded in real product specs, customer feedback, and press coverage. No speculation.

## Limitations & Future Work

- Instagram/Facebook/TikTok data relies on web search and browser verification (these platforms block API access)
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

**Last updated:** July 8, 2026 | **Data as of:** July 8, 2026
