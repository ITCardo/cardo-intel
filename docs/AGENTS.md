# Research Scripts & Workflow

This document details each script in the Cardo competitive intelligence pipeline, what it does, and how to run it manually.

## Overview: 4 Scripts, One Weekly Pipeline

There's no "agent framework" or CLI here — these are plain Python scripts that call the Anthropic API (via the `anthropic` Python SDK) using Claude's built-in `web_search` tool for live research, plus the `keepa` package for Amazon pricing. GitHub Actions runs them in sequence once a week (see `docs/GITHUB_ACTIONS.md` for the exact job graph).

```
┌────────────────────────────────────────────────────────────┐
│ WEEKLY REFRESH (GitHub Actions, Mondays 14:00 UTC)          │
└────────────────────────────────────────────────────────────┘
     │
     ├─ JOB 1: determine-brands ───────────────────────────────
     │   Reads research/brands.json → brand slug list (currently
     │   cardo, sena, asmax, reso)
     │
     ├─ JOB 2: research-agents (one per brand, in parallel) ───
     │   scripts/research_agent.py <slug>
     │   → updates research/<slug>.json (products, news, press,
     │     firmware, social handles) and pulls Amazon pricing via
     │     keepa_scan.py into that file's amazon_pricing key
     │
     ├─ JOB 3: social-listeners ───────────────────────────────
     │   scripts/social_media_listener.py       (Reddit, via web_search)
     │   scripts/apify_social_listener.py       (Facebook Groups +
     │                                            Instagram, via Apify)
     │   → both append to customer_feedback[] in each brand JSON
     │
     └─ JOB 4: publish ────────────────────────────────────────
         scripts/product_expert.py  → regenerates product_insights.json
         python build.py            → renders dashboard.html/index.html
         scripts/validate_dashboard_js.py → sanity-checks embedded JS
         git commit + push          → GitHub Pages picks it up
```

## Individual Script Descriptions

### 1. Research Agent — `scripts/research_agent.py`
**Covers:** One competitor brand per run (cardo, sena, asmax, reso — read from `research/brands.json`)
**Run frequency:** Weekly, once per brand, in parallel (GitHub Actions matrix job)
**Duration:** ~2-3 minutes per brand
**Tools used:** Anthropic Python SDK with Claude's `web_search` tool (no external scraping service); `scripts/keepa_scan.py` (imported as a module) for Amazon pricing when `KEEPA_API_KEY` is set

#### What It Does
Gathers competitive intelligence on its assigned brand:
- **New product launches** (intercoms, smart helmets, new models)
- **Price changes** (MSRP and street prices, sourced via web search of retailer sites)
- **Recent news** (partnerships, firmware announcements, distribution moves)
- **Press coverage** (reviews from motorcycle outlets: MCN, webBikeWorld, RevZilla, FortNine, Bennetts, RideApart, Cycle World, Motorcycle.com)
- **Firmware and app updates** (version history, release notes, user manuals)
- **Amazon pricing/rank** — pulled directly from the Keepa API for the brand's tracked ASINs (see `research/keepa_asins.json`), not scraped

#### How It Works
1. Calls Claude with the `web_search` tool, scoped to the brand's official site, retailers, and press outlets
2. Synthesizes findings into the brand's existing JSON structure
3. If `KEEPA_API_KEY` is configured, calls `fetch_brand_pricing()` from `keepa_scan.py` for the brand's ASINs and writes the result into `amazon_pricing`; if the key is missing or the brand has no ASINs listed, this step is skipped cleanly and `amazon_pricing` is simply left as-is
4. Updates `research/<slug>.json` with findings

#### Data Updated in `<slug>.json`
- `products[]` — add new models with specs (name, tier, price, intercom_tech, range, max_riders, audio, talk_time, waterproof, features, dimensions)
- `recent_news[]` — append {date, headline, source, url}
- `press_coverage.reviews[]` — append {outlet, product, date, rating, url}
- `social_media.recent_posts[]` — append {date, platform, summary, url}
- `firmware_updates[]` — append {date, product, type, version, title, changes, url, source}
- `current_software` — update app versions if newer release found
- `product_firmware[]` — upsert {product, firmware_version, firmware_last_updated, release_notes_url, user_manual_url, support_url}
- `amazon_pricing` — Keepa snapshot (current price, sales rank, rating) for tracked ASINs
- `customer_feedback[]` — **not** touched here; populated by the two social listener scripts below

#### Critical Notes
- **Preserve schema** — Never rename or remove keys. Only update values.
- **Dates must be YYYY-MM-DD** format
- **All URLs must be real and working** — Never fabricate a URL; if you can't find a source, set to null
- **Product specs** — Copy exact names from official sources or press (e.g., "Packtalk Pro", not "Packtalk pro" or "Pro")
- **Price data** — Use street price if available; fall back to MSRP if not
- **Validate JSON** before finishing: `python3 -c "import json; json.load(open('research/cardo.json'))"`

---

### 2. Social Media Listener (Reddit) — `scripts/social_media_listener.py`
**Covers:** All brands, cross-brand
**Run frequency:** Weekly, once (after all research-agents finish)
**Duration:** ~3-4 minutes
**Tools used:** Anthropic Python SDK with Claude's `web_search` tool, capped at 8 searches per run

#### What It Does
Collects real customer feedback from Reddit only:
- **r/motorcyclegear subreddit** — searches for each brand's name and product terms (from `research/brands.json` → `reddit_terms`)
- Classifies sentiment (positive/negative/mixed/neutral) and topic
- **Never invents posts** — only adds entries for real, verifiable customer voices
- Explicitly does not touch Facebook or Instagram — that's `apify_social_listener.py`'s job (see below)

---

### 3. Apify Social Listener (Facebook + Instagram) — `scripts/apify_social_listener.py`
**Covers:** All brands, cross-brand
**Run frequency:** Weekly, once (runs alongside the Reddit listener)
**Duration:** ~3-5 minutes, depending on Apify actor queue time
**Tools used:** Apify's hosted `apify/facebook-groups-scraper` and `apify/instagram-scraper` actors, called via plain HTTPS requests to `api.apify.com`; results are then classified/summarized by Claude

#### What It Does
Pulls real Facebook Group posts and Instagram posts for each brand (group URLs and Instagram handles come from `research/brands.json`), then uses Claude to classify sentiment and deduplicate against what's already in `customer_feedback[]` (by post URL).

#### Important: this one is a hard requirement, not optional
Unlike the Keepa pricing step, this script treats `APIFY_API_TOKEN` as required — if it's not set, it exits with an error (`sys.exit(1)`) instead of skipping gracefully. Because the workflow's `publish` job depends on the `social-listeners` job completing, a missing `APIFY_API_TOKEN` blocks that week's entire site update, not just the Facebook/Instagram data. See `docs/GITHUB_ACTIONS.md` and `AUTOMATION_SETUP.md` for the secret setup and the failure mode this causes.

#### Data Structure (appended to each brand's `customer_feedback[]`, same shape used by the Reddit listener)
```json
{
  "date": "YYYY-MM-DD",
  "source": "Reddit" | "Facebook Group" | "Instagram",
  "forum": "r/motorcyclegear" | "<Facebook Group Name>" | "<Instagram handle>",
  "product": "<exact product name from products[]>" | "General",
  "sentiment": "positive" | "negative" | "mixed" | "neutral",
  "topic": "Pairing issues", "Battery life complaint", "Price complaint", etc.,
  "summary": "1-3 sentence real paraphrase, no fabrication",
  "url": "real URL to the thread/post"
}
```

#### Critical Rules (both listener scripts)
- **Only real posts** — Do not fabricate customer feedback
- **No duplicate URLs** — Both scripts dedupe against existing entries before appending
- **No smart quotes** — Use straight ASCII quotes in JSON
- **Exact product names** — "Packtalk Pro", not "Packtalk pro" or variations

---

### 4. Product Expert — `scripts/product_expert.py`
**Covers:** All brands, synthesizes everything else
**Run frequency:** Weekly, once (last step before build.py, inside the `publish` job)
**Duration:** ~2-4 minutes
**Tools used:** Anthropic Python SDK (no web search — this is pure synthesis over already-gathered data)

#### What It Does
Acts as a senior product manager analyzing ALL competitive intelligence:
- Reads all brand JSONs (products, news, press, social, customer feedback, firmware, Amazon pricing)
- Reads `gap_analysis.json` and `battles.json`
- Synthesizes an original strategic brief on Cardo's competitive position
- Regenerates `research/product_insights.json` **from scratch each run** so analysis always reflects the latest data

#### Output: `product_insights.json` Schema
```json
{
  "generated": "YYYY-MM-DD",
  "analyst_note": "<2-4 sentence opinionated brief on Cardo's position>",
  "executive_summary": "<2-3 paragraphs of strategic analysis>",

  "market_pulse": [
    { "date": "YYYY-MM-DD", "brand": "Sena|Cardo|ASMAX|Reso",
      "development": "<what happened>", "implication": "<why it matters>" },
    ...
  ],

  "gaps": [
    { "title": "Gap title",
      "severity": "critical|high|medium|low",
      "category": "product|pricing|software|gtm|support",
      "description": "<2-3 sentences>",
      "evidence": ["evidence 1", "evidence 2", ...],
      "customer_signal": "<real customer quote or null>",
      "competitor_benchmark": "<how competitor addresses it>" },
    ...
  ],

  "recommendations": [
    { "priority": 1,
      "horizon": "now|next|later",
      "title": "Action title",
      "rationale": "<why this matters>",
      "expected_impact": "<what changes if done>",
      "effort": "low|medium|high",
      "addresses_gaps": ["Gap title 1", "Gap title 2", ...] },
    ...
  ],

  "watchlist": [
    { "item": "<specific competitive move to monitor>",
      "why": "<strategic importance>",
      "trigger": "<concrete event that would signal the threat>" },
    ...
  ]
}
```

#### Quality Bar
- **6-10 market_pulse items** (most strategically significant moves, newest first)
- **6-9 evidence-grounded gaps** (cite real prices, versions, customer complaints from data)
- **5-8 priority-ordered recommendations** (mixed horizons, mapped to gaps)
- **3-5 watchlist items** (with concrete triggers)
- **Senior PM voice** — Opinionated, position-taking, not wishy-washy
- **Every claim grounded in research data** — No invented numbers or hypotheticals
- **Straight ASCII quotes** — Validate JSON before finishing

---

## Per-Brand Notes (what each research agent is watching for)

These are context for interpreting the data, not separate scripts — one `research_agent.py` handles all four brands, driven by the same code path.

### Cardo (research/cardo.json)
- Product tiers: flagship (Packtalk Pro), mid, entry (Packtalk Neo)
- Watch for: Mesh-Boost rollout status, Schuberth/HJC helmet-integration partnerships, warranty policy changes
- Social: Instagram, Facebook, YouTube handles + the Cardo owners Facebook Group (see `research/brands.json`)

### Sena (research/sena.json)
- Product tiers: Flagship (60S EVO, 60X, Stryker), Mid-range (Spider X, Outrush), Value (50S, Spider RT1)
- Smart helmets: Specter, Phantom, Phantom CAM 4K, Impulse, Cavalry, Outlander
- Watch for: lifetime warranty announcements, Wave/Mesh 3.0 cellular rollout progress

### ASMAX (research/asmax.json)
- Aggressive value-tier strategy (F1, S1, Z1, Future 1 line)
- Only brand with substantial presence in Asia/SEA — pricing and news may come from regional sources
- Watch for US retail expansion (Amazon US is the current entry point)

### Reso (research/reso.json)
- Newest entrant (founded 2024), gaining traction on value + features (Pilot Pro, Pilot Neo, Pilot Lite, DuoSync)
- Distribution partnerships (e.g., Daytona in Japan) are the key growth lever — watch for US/EU announcements
- Camera integration (DuoSync records team comms into GoPro footage) is a unique differentiator

---

## How to Run Scripts Manually

### Via GitHub Actions (recommended)
Go to `https://github.com/ITCardo/cardo-intel/actions` → "Weekly Competitive Research Refresh" → **Run workflow**. This runs the full pipeline exactly as the schedule would, using the repo's configured secrets.

### Locally
Each script is a plain Python script — no CLI or agent runtime required, just the secrets as environment variables:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export KEEPA_API_KEY="..."       # optional — Amazon pricing only
export APIFY_API_TOKEN="..."     # required by apify_social_listener.py

pip install anthropic keepa

python scripts/research_agent.py cardo
python scripts/social_media_listener.py
python scripts/apify_social_listener.py
python scripts/product_expert.py
python build.py
```

---

## Error Handling & Troubleshooting

### Script produces invalid JSON
**Symptom:** `build.py` fails with "JSON decode error"
**Fix:**
1. Check for smart quotes (curly “”) instead of straight quotes (")
2. Check for unescaped newlines inside strings
3. Validate with `python3 -c "import json; json.load(open('research/cardo.json'))"`
4. Re-run the script or manually fix the file

### A platform is missing from customer_feedback
**Symptom:** No Facebook or Instagram entries for a brand
**Expected:** Facebook Groups are often member-gated even for Apify's actor, and not every brand has an active Instagram presence to scan. It's fine for a run to add zero entries for a platform.
**Fix:** Don't invent posts; an honest gap is better than fabricated data.

### `apify_social_listener.py` fails the whole run
**Symptom:** `social-listeners` job fails with "APIFY_API_TOKEN not set - skipping (this is a hard requirement, not optional)", and `publish` never runs
**Cause:** This is deliberate in the current code — see script #3 above
**Fix:** Add the `APIFY_API_TOKEN` secret (or, if the intent is genuinely to make Apify optional, that's a code change to `scripts/apify_social_listener.py`, not a config change — see "Adding IP/patent scraping" in the README for the general shape of that kind of work)

### GitHub Pages is stale (live site didn't update)
**Symptom:** A run succeeded but https://itcardo.github.io/cardo-intel/ shows old data
**Fix:**
1. Confirm the `publish` job actually ran (check it wasn't blocked by a failed `social-listeners` job, per above)
2. Hard-refresh your browser (Cmd+Shift+R) — GitHub Pages itself can take 30-60 seconds to rebuild after a push
3. Check the Actions log for the "Commit and push changes" step to confirm it pushed to `main`

---

## Script Persona & Style Guide

### Research Agent (all brands)
- **Persona:** Diligent competitive analyst, bias toward evidence
- **Tone:** Factual, no hyperbole
- **Approach:** Verify data via multiple sources before adding to JSON
- **Handling unverifiable claims:** Skip them; don't guess

### Social Listeners (Reddit + Apify)
- **Persona:** Community listener, Reddit lurker
- **Tone:** Real and conversational (capture actual customer voice)
- **Approach:** Quote real posts; paraphrase accurately
- **Handling gated/inaccessible content:** Acknowledge the limitation; don't fabricate

### Product Expert
- **Persona:** Senior PM at a tech company, strategic thinker, opinionated but grounded
- **Tone:** Direct, position-taking, evidence-based
- **Approach:** Synthesize across all data; call out threats and opportunities clearly
- **Handling uncertainty:** Acknowledge it; recommend monitoring

---

## Related Files

- `docs/DATA_SCHEMA.md` — Detailed JSON schema for each research file
- `docs/SETUP.md` — Installation and configuration
- `docs/GITHUB_ACTIONS.md` — The workflow that runs these scripts on a schedule
- `build.py` — Build script (reads `research/brands.json`, all brand JSONs, `gap_analysis.json`, `battles.json`, `product_insights.json`, `research_summaries.json`; embeds it all into the dashboard HTML)
- `README.md` — High-level system overview

---

**Last updated:** September 29, 2026
