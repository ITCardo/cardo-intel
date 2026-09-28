# Agent Descriptions & Workflow

This document details each Claude AI agent in the Cardo competitive intelligence system, what it does, and how to spawn/monitor it.

## Overview: 6 Agents + Orchestration

```
┌────────────────────────────────────────────────────────────┐
│ DAILY REFRESH ORCHESTRATOR                                │
│ (Spawned by user or scheduled task)                        │
│ Coordinates phases 1-4 and monitors for completion         │
└────────────────────────────────────────────────────────────┘
     │
     ├─ PHASE 1: Run 5 research agents in parallel ────────────┐
     │                                                          │
     ├─► 1. Cardo Research Agent    (research/cardo.json)      │
     ├─► 2. Sena Research Agent     (research/sena.json)       │
     ├─► 3. ASMAX Research Agent    (research/asmax.json)      │
     ├─► 4. Reso Research Agent     (research/reso.json)       │
     ├─► 5. Social Media Listener   (all 4 brands' feedback)   │
     │                                                          │
     ├─ PHASE 2: Update derived analysis (manual or auto)      │
     │                                                          │
     ├─ PHASE 2b: Run Product Expert Agent ──────────────────┐
     │   (After phase 1 completes)                            │
     │   → Regenerates research/product_insights.json         │
     │                                                          │
     └─ PHASE 3-4: Build, validate, publish ─────────────────┘
         (After phase 2b completes)
         → run build.py
         → validate JS
         → git commit + push
         → verify deployment
```

## Individual Agent Descriptions

### 1. Cardo Research Agent
**Type:** Trend Researcher (brand: Cardo Systems)
**File:** `research/cardo.json`
**Run frequency:** Daily (7 AM) or on-demand
**Duration:** ~2-3 minutes
**Tools:** Bash, firecrawl CLI, web search

#### What It Does
Gathers competitive intelligence on Cardo, specifically:
- **New product launches** (motorcycles, smart helmets, new intercom models)
- **Price changes** (MSRP and street prices on RevZilla, Amazon, official sites)
- **Recent news** (partnerships, firmware announcements, distribution moves)
- **Press coverage** (reviews from motorcycle outlets: MCN, webBikeWorld, RevZilla, FortNine, Bennetts, RideApart, Cycle World, Motorcycle.com)
- **Social media posts** (Instagram, Facebook, YouTube, Reddit — aggregating public content)
- **Firmware and app updates** (version history, release notes, user manuals)

#### How It Works
1. Scans Cardo's official site (cardosystems.com, product pages)
2. Checks RevZilla and Amazon for current pricing
3. Uses `firecrawl search` to find recent news and press coverage
4. Searches YouTube and Reddit for community discussions
5. Attempts Facebook group scrapes (usually member-gated, limited success)
6. Checks app stores (iOS App Store, Google Play) for companion app versions
7. Updates `research/cardo.json` with findings

#### Data Updated in `cardo.json`
- `products[]` — add new models with specs (name, tier, price, intercom_tech, range, max_riders, audio, talk_time, waterproof, features, dimensions)
- `recent_news[]` — append {date, headline, source, url}
- `press_coverage.reviews[]` — append {outlet, product, date, rating, url}
- `social_media.recent_posts[]` — append {date, platform, summary, url}
- `firmware_updates[]` — append {date, product, type, version, title, changes, url, source}
- `current_software` — update app versions if newer release found
- `product_firmware[]` — upsert {product, firmware_version, firmware_last_updated, release_notes_url, user_manual_url, support_url}
- `customer_feedback[]` — (populated by Social Media Listener, not this agent)

#### Critical Notes
- **Preserve schema** — Never rename or remove keys. Only update values.
- **Dates must be YYYY-MM-DD** format
- **All URLs must be real and working** — Never fabricate a URL; if you can't find a source, set to null
- **Product specs** — Copy exact names from official sources or press (e.g., "Packtalk Pro", not "Packtalk pro" or "Pro")
- **Price data** — Use street price if available; fall back to MSRP if not
- **Validate JSON** before finishing: `python3 -c "import json; json.load(open('research/cardo.json'))"`

---

### 2. Sena Research Agent
**Type:** Trend Researcher (brand: Sena)
**File:** `research/sena.json`
**Run frequency:** Daily (7 AM) or on-demand
**Duration:** ~2-3 minutes
**Tools:** Bash, firecrawl CLI, web search

#### What It Does
Same as Cardo Research Agent, but focused on Sena:
- New Sena product launches (Specter, Phantom, Spider X Slim, 60X, 60S EVO, Vortex, etc.)
- Pricing (store-us.sena.com, RevZilla, Amazon)
- News and partnerships (especially major launches like Wave, MeshON)
- Press (more extensive Western coverage than competitors)
- Social media (Sena has high engagement on Instagram)
- Firmware (especially the recent Wave cellular and Mesh 3.0 rollouts)

#### Data Updated in `sena.json`
Same fields as Cardo agent (products, recent_news, press_coverage, social_media, firmware_updates, current_software, product_firmware).

#### Special Attention
- Sena's product tiers: Flagship (60S EVO, 60X, Stryker), Mid-range (Spider X, Outrush), Value (50S, Spider RT1)
- Smart helmets: Specter, Phantom, Phantom CAM 4K, Impulse, Cavalry, Outlander
- Watch for lifetime warranty announcements (major competitive move)

---

### 3. ASMAX Research Agent
**Type:** Trend Researcher (brand: ASMAX)
**File:** `research/asmax.json`
**Run frequency:** Daily (7 AM) or on-demand
**Duration:** ~2-3 minutes
**Tools:** Bash, firecrawl CLI, web search

#### What It Does
Tracks ASMAX's aggressive value-tier strategy:
- Product launches (F1s, S1, Z1, Future 1 line)
- Pricing (asmaxworld.com, Amazon US, Asian pricing for regional analysis)
- News (AIMExpo presence, motorsport sponsorships, Mode feature rollout)
- Press (minimal Western coverage; mostly reviews from YouTube influencers and regional outlets)
- Social media (Instagram, YouTube, Facebook group — ASMAX is very active in rider communities)
- Firmware (ASMAX World app updates, FOTA releases)

#### Data Updated in `asmax.json`
Same fields as other brand agents.

#### Special Attention
- ASMAX is only brand with substantial presence in Asia/SEA — pricing and news may come from regional sources
- Budget-focused positioning (Hi Max AI, CloudTalk hybrid mesh) attracts different buyer than Cardo/Sena
- Watch for US retail expansion (Amazon US is current entry point)

---

### 4. Reso Research Agent
**Type:** Trend Researcher (brand: Reso)
**File:** `research/reso.json`
**Run frequency:** Daily (7 AM) or on-demand
**Duration:** ~2-3 minutes
**Tools:** Bash, firecrawl CLI, web search

#### What It Does
Monitors a smaller but aggressive challenger:
- Product launches (Pilot Pro, Pilot Neo, Pilot Lite, DuoSync)
- Pricing (resosport.com main channel; minimal retail presence)
- News (Daytona distribution deal June 2026 was major; distribution expansion is primary growth vector)
- Press (mostly regional/Asian outlets; Western press coverage is sparse)
- Social media (growing YouTube presence; Instagram shows lifestyle/adventure positioning)
- Firmware (Reso Link app updates)

#### Data Updated in `reso.json`
Same fields as other brand agents.

#### Special Attention
- Reso is the newest entrant (founded 2024) but gaining traction with value + features strategy
- Distribution partnerships (Daytona in Japan) are key growth lever — watch for US/EU announcements
- Camera integration (DuoSync records team comms into GoPro footage) is unique differentiator

---

### 5. Social Media Listener Agent
**Type:** Cross-brand customer feedback aggregator
**Files:** Appends to `customer_feedback[]` in all 4 brand JSONs
**Run frequency:** Daily (7 AM) or on-demand
**Duration:** ~3-4 minutes
**Tools:** Bash, web search, Reddit API (optional), firecrawl search

#### What It Does
Collects real customer feedback from forums and subreddits:
- **Cardo owners Facebook group** — https://www.facebook.com/groups/1847605508861922
- **Sena owners Facebook group** — https://www.facebook.com/groups/860066485997389
- **ASMAX owners Facebook group** — https://www.facebook.com/groups/1275973273584175
- **Reso owners Facebook group** — https://www.facebook.com/groups/1004405754956044
- **r/motorcyclegear subreddit** — Search for each brand (Cardo, Sena, ASMAX, Reso)

#### How It Works
1. Searches Reddit (public, indexable) for brand mentions and product discussions
2. Attempts Facebook group scrapes (most are member-gated; limited success)
3. Identifies real posts with sentiment, topic, product, and quotes
4. **Never invents posts** — only adds entries for real, verifiable customer voices

#### Data Structure (appended to each brand's `customer_feedback[]`)
```json
{
  "date": "YYYY-MM-DD",
  "source": "Reddit" | "Facebook Group",
  "forum": "r/motorcyclegear" | "<Facebook Group Name>",
  "product": "<exact product name from products[]>" | "General",
  "sentiment": "positive" | "negative" | "mixed" | "neutral",
  "topic": "Pairing issues", "Battery life complaint", "Price complaint", etc.,
  "summary": "1-3 sentence real paraphrase, no fabrication",
  "url": "real URL to the thread/post or forum main URL"
}
```

#### Critical Rules
- **Only real posts** — Do not fabricate customer feedback
- **No duplicate dates/topics** — Check before appending
- **Real URLs only** — If you can't find a real link, use the forum's main URL as fallback
- **No smart quotes** — Use straight ASCII quotes in JSON
- **Exact product names** — "Packtalk Pro", not "Packtalk pro" or variations

#### Quality Bar
- Typical output: 30-50 new entries per cycle (mix of brands)
- Majority from Reddit (r/motorcyclegear is active)
- Facebook groups yield 5-15 entries (member-gated, limited accessibility)

---

### 6. Product Expert Agent
**Type:** Senior PM analysis / strategic synthesis
**File:** Regenerates `research/product_insights.json` from scratch
**Run frequency:** Daily (after phases 1-2 complete) or on-demand
**Duration:** ~5-8 minutes
**Tools:** All tools (reads all research files, writes JSON)

#### What It Does
Acts as a senior product manager analyzing ALL competitive intelligence:
- Reads all 4 brand JSONs (products, news, press, social, customer feedback, firmware)
- Reads `gap_analysis.json` and `battles.json`
- Synthesizes an original strategic brief on Cardo's competitive position
- Regenerates `research/product_insights.json` **from scratch each day** so analysis always reflects latest data

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

#### Example Insights from July 2026
```
analyst_note: "Cardo still owns group intercom reliability and wins 'best overall' 
titles, but the company is harvesting rather than defending that reputation. 
The 2025 price hikes, 18-month Mesh-Boost delivery mess, and no-mesh-under-$360 
gap have opened three flanks while Sena ships three Bose flagships at $459 and 
two Chinese challengers reset the price floor."

gaps: [
  {
    "title": "No mesh below $360",
    "severity": "critical",
    "evidence": [
      "Packtalk Neo $359.95 is Cardo's cheapest mesh",
      "Sena Spider X Slim $299 (Bose, lifetime warranty)",
      "ASMAX S1 $89.99 with offline AI"
    ],
    "customer_signal": "r/motorcyclegear: 'insane that cardos cost more than actual helmets'",
    "competitor_benchmark": "Sena Spider X Slim: $299 mesh with Bose and lifetime warranty"
  }
]

watchlist: [
  {
    "item": "ASMAX US retail arrival",
    "why": "ASMAX's 2025 flagship at $155-269 is only Asia-only; US arrival would legitimize budget tier",
    "trigger": "F1 Pro Max listed on Amazon US or first tier-1 review (FortNine, webBikeWorld)"
  }
]
```

---

## How to Spawn Agents Manually

### Via Claude Code CLI
```bash
# Spawn a single research agent (example: Cardo)
claude agent run "Cardo research agent - products, news, press, social, firmware" \
  --model claude-opus-4-8

# Spawn all 5 research agents in parallel
# (Requires multiple Claude sessions or batched agent spawning)
```

### Via Scheduled Task
The system has a pre-configured scheduled task `daily-competitor-research-refresh` that:
1. Spawns all 5 research agents in parallel
2. Monitors for completion via file changes
3. Spawns Product Expert agent
4. Runs build.py
5. Validates and publishes

To manually trigger:
```bash
# Use Claude Code dashboard → Scheduled section → daily-competitor-research-refresh → "Run Now"
# Or via CLI if available:
claude schedule run daily-competitor-research-refresh
```

---

## Error Handling & Troubleshooting

### Agent produces invalid JSON
**Symptom:** `build.py` fails with "JSON decode error"
**Fix:** 
1. Check for smart quotes (curly "") instead of straight quotes (")
2. Check for unescaped newlines inside strings
3. Validate with `python3 -c "import json; json.load(open('research/cardo.json'))"`
4. Rerun the agent or manually fix the file

### Agent skips a source/brand
**Symptom:** No Instagram posts in social_media.recent_posts[]
**Expected:** Instagram/Facebook/TikTok data is hard to scrape; agents rely on web search and browser verification. It's fine to skip a platform.
**Fix:** Don't invent posts; an honest gap is better than fabricated data.

### Agent takes >5 minutes
**Symptom:** Agent is still running after 5 minutes
**Expected:** Firecrawl has concurrency limits (2 shared jobs); agents may wait their turn. Up to 8 minutes is normal.
**Fix:** Let it finish. If it's stuck >10 minutes, kill and rerun.

### GitHub Pages is stale (live site didn't update)
**Symptom:** You pushed code but https://itcardo.github.io/cardo-intel/ shows old data
**Root cause:** Often a bare `git push` that accidentally pushed to the wrong branch (e.g., `daily-refresh-2026-07-08` instead of `main`)
**Fix:**
1. Verify local branch: `git status` → should show "On branch main"
2. Verify remote: `git push origin HEAD:main` (explicit target, not bare push)
3. Check GitHub Pages status: `gh api repos/ITCardo/cardo-intel/pages/builds/latest`
4. Force rebuild if stuck: `gh api repos/ITCardo/cardo-intel/pages/builds -X POST`

---

## Agent Persona & Style Guide

### Research Agents (Cardo, Sena, ASMAX, Reso)
- **Persona:** Diligent competitive analyst, bias toward evidence
- **Tone:** Factual, no hyperbole
- **Approach:** Verify data via multiple sources before adding to JSON
- **Handling unverifiable claims:** Skip them; don't guess

### Social Media Listener
- **Persona:** Community listener, Reddit lurker
- **Tone:** Real and conversational (capture actual customer voice)
- **Approach:** Quote real posts; paraphrase accurately
- **Handling member-gated content:** Acknowledge the limitation; don't fabricate

### Product Expert
- **Persona:** Senior PM at a tech company, strategic thinker, opinionated but grounded
- **Tone:** Direct, position-taking, evidence-based
- **Approach:** Synthesize across all data; call out threats and opportunities clearly
- **Handling uncertainty:** Acknowledge it; recommend monitoring

---

## Related Files

- `~/.claude/scheduled-tasks/daily-competitor-research-refresh/SKILL.md` — Full workflow definition
- `docs/DATA_SCHEMA.md` — Detailed JSON schema for each research file
- `docs/SETUP.md` — Installation and configuration
- `build.py` — Build script (reads all 6 JSONs, embeds in HTML)
- `README.md` — High-level system overview

