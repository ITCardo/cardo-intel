# Installation & Local Setup Guide

This guide covers setting up the Cardo competitive intelligence dashboard on your own machine.

## System Requirements

- **Python 3.8+** (for `build.py` and all scripts in `scripts/`)
- **Node.js** (optional — only used to syntax-check the dashboard's embedded JavaScript during build)
- **Git** (for version control and GitHub integration)
- **Bash/Zsh** (Unix-like shell)

That's it — there's no Firecrawl CLI, no GitHub CLI (`gh`), and no separate "Claude CLI". The research scripts call the Anthropic API directly through the `anthropic` Python package, and publishing is a plain `git push`.

### Operating Systems Tested
- macOS 12+ (Monterey or later)
- Linux (Ubuntu 20.04+)
- Windows (via WSL2 or similar)

---

## Step 1: Clone or Set Up the Repository

### Option A: Clone from GitHub (if already pushed)
```bash
git clone https://github.com/ITCardo/cardo-intel.git
cd cardo-intel
```

### Option B: Initialize a new repository locally
```bash
mkdir cardo-intel
cd cardo-intel
git init
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

---

## Step 2: Set Up Python Environment

### 2a. Create a virtual environment (recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2b. Install Python dependencies
`build.py` itself has **no external dependencies** beyond the standard library. The research scripts need two packages:

```bash
pip install --upgrade pip
pip install anthropic keepa
```

- `anthropic` — used by every script that calls Claude (`research_agent.py`, `social_media_listener.py`, `apify_social_listener.py`, `product_expert.py`)
- `keepa` — used by `scripts/keepa_scan.py` (imported by `research_agent.py`) to pull Amazon pricing/rank data; only needed if you're using `KEEPA_API_KEY`

`apify_social_listener.py` talks to Apify over plain HTTPS (`urllib.request`) — no Apify SDK required.

---

## Step 3: Set Up API Keys

Three services are involved. All are read from environment variables — never hardcode a key in a script.

```bash
# Add to ~/.bashrc, ~/.zshrc, or a git-ignored .env file:
export ANTHROPIC_API_KEY="sk-ant-..."     # required — get from https://console.anthropic.com
export KEEPA_API_KEY="..."                # optional — get from https://keepa.com (account settings → API)
export APIFY_API_TOKEN="..."              # required by apify_social_listener.py — get from https://console.apify.com (Settings → Integrations)
```

`ANTHROPIC_API_KEY` is required for every script. `KEEPA_API_KEY` is genuinely optional — Amazon pricing data is simply skipped if it's unset. `APIFY_API_TOKEN` is *not* optional as `apify_social_listener.py` is currently written: it exits with an error if missing (see `docs/AGENTS.md` and `AUTOMATION_SETUP.md` for what that breaks downstream in the GitHub Actions pipeline).

---

## Step 4: Set Up GitHub Integration (for publishing)

### 4a. Add the GitHub remote (if not already done)
```bash
# From inside your cardo-intel directory
git remote add origin https://github.com/ITCardo/cardo-intel.git
git branch -M main
```

### 4b. Push and enable Pages
```bash
git add .
git commit -m "Initial commit"
git push -u origin main
```

Then in GitHub: **Settings → Pages** → Source = `main` branch, `/ (root)` folder. No CLI step needed — this is a one-time setting in the repo's web UI.

---

## Step 5: Verify the Build Pipeline

### 5a. Build the dashboard locally
```bash
python3 build.py
```

Expected output:
```
dashboard.html + index.html written (395,123 bytes)
```

### 5b. Open the dashboard
```bash
# Option 1: Direct file (works from file://)
open dashboard.html

# Option 2: Via HTTP server (to test full functionality)
python3 -m http.server 8000
# Then open http://localhost:8000/dashboard.html
```

### 5c. Validate JavaScript (optional, requires Node.js)
```bash
python3 scripts/validate_dashboard_js.py
```
This is the same check the GitHub Actions `publish` job runs before committing.

---

## Step 6: Run the Research Scripts Locally

With the environment variables from Step 3 set:

```bash
python scripts/research_agent.py cardo    # repeat for sena, asmax, reso
python scripts/social_media_listener.py   # Reddit feedback, all brands
python scripts/apify_social_listener.py   # Facebook Group + Instagram feedback, all brands
python scripts/product_expert.py          # regenerates product_insights.json
```

See `docs/AGENTS.md` for what each script actually does and what it writes.

---

## Directory Structure After Setup

```
cardo-intel/
├── .git/                        # Git repository
├── .gitignore                   # Ignored files
├── README.md                    # Main documentation
├── build.py                     # Build script (main tool)
├── dashboard_template.html      # HTML template (do not edit directly)
├── dashboard.html               # (generated) Final dashboard
├── index.html                   # (generated) Copy deployed alongside dashboard.html
│
├── docs/
│   ├── SETUP.md                 # This file
│   ├── AGENTS.md                 # Script descriptions
│   ├── GITHUB_ACTIONS.md         # Workflow reference
│   └── DATA_SCHEMA.md            # JSON schema reference
│
├── scripts/
│   ├── research_agent.py         # Per-brand research (products, news, press, firmware, Keepa pricing)
│   ├── keepa_scan.py             # Amazon pricing module (imported by research_agent.py; also runnable standalone)
│   ├── social_media_listener.py  # Reddit customer feedback
│   ├── apify_social_listener.py  # Facebook Group + Instagram customer feedback (via Apify)
│   ├── product_expert.py         # Synthesizes product_insights.json
│   └── validate_dashboard_js.py  # Syntax-checks the dashboard's embedded JS
│
├── research/
│   ├── brands.json              # Central config: which brands the pipeline tracks
│   ├── cardo.json               # Brand data (products, news, press, social, firmware, feedback, Amazon pricing)
│   ├── sena.json
│   ├── asmax.json
│   ├── reso.json
│   ├── keepa_asins.json         # Which Amazon ASINs to track per brand
│   ├── keepa_pricing.json       # (generated, optional) standalone output if you run keepa_scan.py directly
│   ├── gap_analysis.json
│   ├── battles.json
│   ├── product_insights.json
│   └── research_summaries.json  # Human-readable per-brand summary blurbs shown on the dashboard
│
└── .github/workflows/daily-refresh.yml   # The weekly GitHub Actions pipeline
```

---

## Common Setup Issues & Troubleshooting

### Issue: "Python 3 not found"
```bash
python3 --version
# macOS: brew install python3
# Ubuntu: sudo apt-get install python3
```

### Issue: "build.py fails with JSON error"
```bash
# Check for JSON syntax errors in research files:
python3 -c "import json; json.load(open('research/cardo.json'))"
# This will show the exact line with the error
```

### Issue: "ModuleNotFoundError: No module named 'anthropic'" (or 'keepa')
```bash
pip install anthropic keepa
```

### Issue: "apify_social_listener.py exits immediately"
```bash
# It requires APIFY_API_TOKEN to be set — this is intentional, not a bug:
echo $APIFY_API_TOKEN   # should not be empty
```

### Issue: "Can't open dashboard.html in browser"
```bash
# Use an HTTP server instead of file:// (more reliable):
python3 -m http.server 8000
# Then open http://localhost:8000/dashboard.html
```

---

## Development Workflow

### Workflow for Local Research Updates

1. **Edit research data**:
   ```bash
   vim research/cardo.json
   ```

2. **Validate JSON**:
   ```bash
   python3 -c "import json; json.load(open('research/cardo.json'))"
   ```

3. **Rebuild dashboard**:
   ```bash
   python3 build.py
   ```

4. **Preview**:
   ```bash
   python3 -m http.server 8000 &
   open http://localhost:8000/dashboard.html
   ```

5. **Commit changes**:
   ```bash
   git add research/cardo.json dashboard.html index.html
   git commit -m "Update Cardo pricing and product info"
   git push origin main
   ```

### Workflow for Running Scripts Locally Instead of Waiting for the Schedule

1. **Run the scripts you need** (see Step 6 above), which updates `research/*.json`
2. **Check what changed**:
   ```bash
   git status
   ```
3. **Rebuild and publish**:
   ```bash
   python3 build.py
   git add research/*.json dashboard.html index.html
   git commit -m "Manual data refresh $(date +%Y-%m-%d)"
   git push origin main
   ```
4. **Verify deployment** — a plain local `git push` does **not** trigger the Azure deploy: `.github/workflows/daily-refresh.yml` only runs on its Monday schedule or a manual "Run workflow" click, not on `push`. So after pushing a manual refresh, also trigger the workflow (Actions tab → "Weekly Competitive Research Refresh" → "Run workflow") so its `publish` job's "Deploy to Azure Static Web Apps" step actually runs; then confirm at https://cardo-intel.cardosystems.com/ (sign-in required) after ~30-60 seconds, and check the commit shows up: `git log -1`

---

## Performance Notes

- **build.py runtime:** <1 second (simple JSON embedding)
- **Research agent runtime:** 2-3 minutes per brand
- **Social listener runtime:** 3-5 minutes each (Reddit and Apify listeners run separately)
- **Product Expert runtime:** 2-4 minutes
- **Full weekly refresh cycle:** ~15-20 minutes end to end (all brands in parallel + both listeners + product expert + build + publish)
- **Azure Static Web Apps deployment:** 30-60 seconds after the `publish` job's deploy step runs
- **Dashboard load time:** <2 seconds (single HTML file, self-contained)

---

## Security Considerations

1. **API Keys:** Store in environment variables or `.env` files (git-ignored), never in code
2. **GitHub Actions secrets:** In production, all three keys (`ANTHROPIC_API_KEY`, `KEEPA_API_KEY`, `APIFY_API_TOKEN`) live as encrypted repository secrets, not local files — see `AUTOMATION_SETUP.md`
3. **Apify data source:** Facebook Group and Instagram data comes through Apify's hosted scraping actors, not a locally-run scraper — see `docs/AGENTS.md` for the ToS considerations worth flagging to anyone reviewing this pipeline
4. **GitHub push access:** Whoever holds write access to `main` can trigger a publish; keep collaborator access on the repo limited

### Recommended .gitignore
```
venv/
.DS_Store
.env
.env.keepa
out/
*.pyc
__pycache__/
```

---

## Next Steps

1. **Run the build:**
   ```bash
   python3 build.py
   ```

2. **Open the dashboard:**
   ```bash
   python3 -m http.server 8000
   # Open http://localhost:8000/dashboard.html
   ```

3. **Explore the docs:**
   - `docs/AGENTS.md` — Learn about the research scripts
   - `docs/DATA_SCHEMA.md` — Understand JSON structure
   - `docs/GITHUB_ACTIONS.md` — How the weekly automation works
   - `README.md` — System overview

4. **Set up weekly automation:**
   - See `AUTOMATION_SETUP.md` for the GitHub Actions secrets and schedule

---

## Support & Issues

- **Build.py errors:** Check JSON syntax in `research/*.json`
- **Script errors:** See `docs/AGENTS.md` troubleshooting section
- **Deployment issues:** See `README.md` deployment notes and `AUTOMATION_SETUP.md`
- **General questions:** Read through `README.md` and linked docs first

---

**Last updated:** September 30, 2026
