# Installation & Local Setup Guide

This guide covers setting up the Cardo competitive intelligence dashboard on your own machine.

## System Requirements

- **Python 3.8+** (for build.py)
- **Node.js 12+** (optional, for JavaScript syntax checking)
- **Git** (for version control and GitHub integration)
- **GitHub CLI** (`gh` command) (for publishing to GitHub Pages)
- **Bash/Zsh** (Unix-like shell)
- **firecrawl CLI** (for web research agents)

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
The build script (`build.py`) has **no external Python dependencies** beyond the standard library. However, if you're running research agents or scraper scripts locally, install:

```bash
# For research agents (if running locally, normally run via Claude)
pip install --upgrade pip
# No additional packages needed for build.py itself

# (Optional) If using Instagram scraper locally:
# pip install instagrapi
```

---

## Step 3: Install Firecrawl CLI

Firecrawl is the web scraping tool used by research agents to gather competitive intelligence.

### 3a. Install firecrawl
```bash
# Via npm (Node.js package manager)
npm install -g @firecrawl/cli

# Or via homebrew (macOS)
brew install firecrawl-cli

# Verify installation:
firecrawl --version
```

### 3b. Authenticate with Firecrawl
```bash
# Set your Firecrawl API key (get from firecrawl.dev)
export FIRECRAWL_API_KEY="your-api-key-here"

# Test authentication:
firecrawl search "motorcycle intercom" --limit 1
```

---

## Step 4: Set Up GitHub Integration (Optional, for publishing)

### 4a. Install GitHub CLI
```bash
# macOS
brew install gh

# Ubuntu/Debian
sudo apt-get install gh

# Windows (via scoop)
scoop install gh

# Verify:
gh --version
```

### 4b. Authenticate with GitHub
```bash
gh auth login
# Follow prompts to authorize (browser flow)
```

### 4c. Create a GitHub repository (if not already done)
```bash
# From inside your cardo-intel directory
git remote add origin https://github.com/YOUR_USERNAME/cardo-intel.git
git branch -M main
```

### 4d. Enable GitHub Pages
```bash
# Push initial commit
git add .
git commit -m "Initial commit"
git push -u origin main

# Enable Pages (via CLI)
gh repo edit --enable-issues --enable-projects --enable-wiki

# Or manually in GitHub: Settings → Pages → Source = main branch, root folder
```

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
# Extract and validate the embedded JavaScript
sed -n '/<script>/,/<\/script>/p' dashboard.html | sed '1d;$d' > /tmp/check.js
node -c /tmp/check.js
# Output: "No syntax errors detected" (from Node.js)
```

---

## Step 6: Set Up Claude AI Integration (for agents)

Normally, research agents run via Claude Code or a scheduled task. To run them locally:

### 6a. Install Claude CLI (if not already installed)
```bash
# Via npm
npm install -g @anthropic-ai/claude

# Verify:
claude --version
```

### 6b. Authenticate with Anthropic
```bash
claude auth login
# Follow prompts to set API key
```

### 6c. Set up environment variables
```bash
# Add to ~/.bashrc or ~/.zshrc or .env file:
export ANTHROPIC_API_KEY="your-api-key"
export FIRECRAWL_API_KEY="your-firecrawl-key"
```

---

## Step 7: Optional — Set Up Instagram Scraper

The `ig_product_scan.py` script scans Instagram for product launches (optional, not required for daily refresh).

### 7a. Install instagrapi
```bash
pip install instagrapi
```

### 7b. Set Instagram credentials
```bash
# Create .env.ig file (git-ignored)
echo "IG_USERNAME=your_ig_account" > .env.ig
echo "IG_PASSWORD=your_ig_password" >> .env.ig

# Make sure .env.ig is in .gitignore (it should be)
grep ".env.ig" .gitignore  # Should return ".env.ig"
```

### 7c. Test the scraper
```bash
# Load credentials and run a test scan
source .env.ig
python3 ig_product_scan.py senabluetooth --count 5
```

Expected output: List of recent Sena Instagram posts with product mentions.

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
├── index.html                   # (generated) Copy for GitHub Pages
│
├── docs/
│   ├── SETUP.md                # This file
│   ├── AGENTS.md               # Agent descriptions
│   └── DATA_SCHEMA.md          # JSON schema reference
│
├── research/
│   ├── cardo.json              # Brand data
│   ├── sena.json
│   ├── asmax.json
│   ├── reso.json
│   ├── gap_analysis.json
│   ├── battles.json
│   └── product_insights.json
│
├── ig_product_scan.py          # Instagram scraper (optional)
├── apify_scan.py               # Apify scraper (optional)
├── .env.ig                      # Instagram credentials (git-ignored)
│
├── .firecrawl/                 # (generated) Firecrawl cache
└── venv/                        # (optional) Python virtual environment
```

---

## Common Setup Issues & Troubleshooting

### Issue: "Python 3 not found"
```bash
# Verify Python installation:
python3 --version

# If not installed:
# macOS: brew install python3
# Ubuntu: sudo apt-get install python3
```

### Issue: "build.py fails with JSON error"
```bash
# Check for JSON syntax errors in research files:
python3 -c "import json; json.load(open('research/cardo.json'))"
# This will show the exact line with the error
```

### Issue: "firecrawl command not found"
```bash
# Verify installation:
which firecrawl  # Should return path

# If missing, reinstall:
npm install -g @firecrawl/cli

# Verify API key is set:
echo $FIRECRAWL_API_KEY  # Should not be empty
```

### Issue: "GitHub authentication fails"
```bash
# Re-authenticate:
gh auth logout
gh auth login

# Verify:
gh auth status
```

### Issue: "Can't open dashboard.html in browser"
```bash
# Use an HTTP server instead of file:// (more reliable):
python3 -m http.server 8000
# Then open http://localhost:8000/dashboard.html

# Or use python -m http.server on older Python:
python -m SimpleHTTPServer 8000
```

---

## Development Workflow

### Workflow for Local Research Updates

1. **Edit research data**:
   ```bash
   # Edit one of the brand JSON files
   vim research/cardo.json
   ```

2. **Validate JSON**:
   ```bash
   python3 -c "import json; json.load(open('research/cardo.json'))"
   # No output = valid; error message = fix it
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

### Workflow for Running Agents Locally

1. **Trigger a research agent**:
   ```bash
   # This is normally done via Claude Code or scheduled task
   # For manual testing, you'd call the Claude API directly:
   # (see docs/AGENTS.md for detailed instructions)
   ```

2. **Monitor for file changes**:
   ```bash
   # After agents update research/*.json files:
   git status  # Should show modified files
   ```

3. **Run build pipeline**:
   ```bash
   python3 build.py
   git add .
   git commit -m "Daily data refresh $(date +%Y-%m-%d)"
   git push origin HEAD:main  # Important: explicit target
   ```

4. **Verify deployment**:
   ```bash
   # Check that GitHub Pages picked up the push:
   gh api repos/YOUR_USERNAME/cardo-intel/commits/main --jq .sha
   
   # Should match your local commit:
   git rev-parse HEAD
   
   # Check deployment status:
   gh api repos/YOUR_USERNAME/cardo-intel/pages/builds/latest \
     --jq '.commit + " " + .status'
   ```

---

## Performance Notes

- **build.py runtime:** <1 second (simple JSON embedding)
- **Research agent runtime:** 2-3 minutes per agent (gathering data from web)
- **Product Expert agent runtime:** 5-8 minutes (synthesizing all data)
- **Full daily refresh cycle:** ~15-20 minutes (all 6 agents + build + publish)
- **GitHub Pages deployment:** 30-60 seconds after push
- **Dashboard load time:** <2 seconds (single HTML file, self-contained)

---

## Security Considerations

1. **API Keys:** Store in environment variables or `.env` files (git-ignored), never in code
2. **Instagram credentials:** Use a dedicated/throwaway account (instagrapi uses mobile API, against Instagram ToS)
3. **GitHub token:** Authenticate via `gh auth login` (browser-based, more secure than personal access tokens)
4. **Firecrawl API key:** Keep in `FIRECRAWL_API_KEY` environment variable

### Recommended .gitignore
```
venv/
.DS_Store
.env.ig
.ig_session.json
.firecrawl/
out/
*.pyc
__pycache__/
.env
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
   - `docs/AGENTS.md` — Learn about agents
   - `docs/DATA_SCHEMA.md` — Understand JSON structure
   - `README.md` — System overview

4. **Set up daily refresh:**
   - Via Claude Code scheduled tasks (recommended)
   - Or manually run agents and `build.py` on your own schedule

5. **Deploy to GitHub Pages:**
   - Push to main branch
   - GitHub Pages builds automatically

---

## Support & Issues

- **Build.py errors:** Check JSON syntax in `research/*.json`
- **Agent errors:** See `docs/AGENTS.md` troubleshooting section
- **GitHub Pages issues:** See `README.md` deployment notes
- **General questions:** Read through `README.md` and linked docs first

---

**Last updated:** July 8, 2026
