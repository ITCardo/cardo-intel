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

There is no Firecrawl key — Firecrawl was replaced by Claude's own server-side web search tool, called directly from the research scripts.

---

## Step 2: Enable GitHub Pages

Repo → **Settings → Pages** → Source: "Deploy from a branch" → Branch: `main`, folder `/ (root)`. Once secrets are in place and a run has pushed a fresh `index.html`, the site is live at https://itcardo.github.io/cardo-intel/.

---

## Step 3: Verify It Works

1. Go to `https://github.com/ITCardo/cardo-intel/actions` → "Weekly Competitive Research Refresh" → **Run workflow**.
2. Watch the four jobs run: `determine-brands` → `research-agents` (one per brand, parallel) → `social-listeners` → `publish`. Each shows live status; click into any job for its log.
3. Once `publish` finishes, check https://itcardo.github.io/cardo-intel/ and confirm the dashboard's "last updated" date matches today — a green run can still mean thin results if a step found nothing new, so check the actual content, not just the checkmark.

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
