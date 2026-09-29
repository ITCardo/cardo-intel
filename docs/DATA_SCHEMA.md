# JSON Data Schema Reference

Complete schema documentation for all research JSON files in the Cardo competitive intelligence system.

## Overview

`research/brands.json` is the actual source of truth for which brands exist — the table below lists the four it currently defines (cardo, sena, asmax, reso), but adding a brand there automatically adds a new `research/<slug>.json` to this list (see the README's "Adding a new brand" section). These files, plus a few supporting ones, drive the dashboard:

| File | Purpose | Scope | Written by |
|------|---------|-------|-------|
| `research/brands.json` | Which brands the pipeline tracks | Slug, name, website, social handles, Facebook groups, Reddit search terms | Manual (config) |
| `research/cardo.json` | Cardo Systems competitive data | Brand details, products, news, social, firmware, feedback, Amazon pricing | `scripts/research_agent.py cardo` + both social listener scripts |
| `research/sena.json` | Sena competitive data | Same shape as cardo.json | `scripts/research_agent.py sena` + both social listener scripts |
| `research/asmax.json` | ASMAX competitive data | Same shape as cardo.json | `scripts/research_agent.py asmax` + both social listener scripts |
| `research/reso.json` | Reso competitive data | Same shape as cardo.json | `scripts/research_agent.py reso` + both social listener scripts |
| `research/keepa_asins.json` | Which Amazon ASINs to track, per brand | Config only | Manual (config) |
| `research/keepa_pricing.json` | Standalone Keepa dump | Optional — only produced if you run `scripts/keepa_scan.py` directly; the automated pipeline writes pricing straight into each brand's `amazon_pricing` key instead | `scripts/keepa_scan.py` (manual/standalone use) |
| `research/gap_analysis.json` | Cardo's strategic gaps | Feature gaps, pricing gaps, severity | Manual or analyst |
| `research/battles.json` | Head-to-head comparisons | 16-dimension capability matrix | Manual or analyst |
| `research/product_insights.json` | Strategic analysis | Market pulse, gaps, recommendations, watchlist | `scripts/product_expert.py` |
| `research/research_summaries.json` | Human-readable per-brand summary blurbs (mirrors the `.md` notes files) | Free text shown on the dashboard | Manual/analyst |

---

## Brand Research Files (cardo.json, sena.json, asmax.json, reso.json)

All four brand files share the same schema. Here's the complete structure:

```json
{
  "competitor": "Cardo|Sena|ASMAX|Reso",
  "website": "https://cardosystems.com",
  "company": {
    "founded": 2003,
    "hq": "Israel",
    "description": "Premium group motorcycle communicator brand, pioneer of DMC mesh"
  },

  "products": [
    {
      "name": "Packtalk Pro",
      "tier": "flagship|mid|entry",
      "category": "communicator|smart_helmet",
      "msrp_usd": 499.95,
      "street_price_usd": 449.95,
      "intercom_tech": "DMC Gen2 mesh (31 riders), auto-pairing, universal bridging",
      "range_km": 1.6,
      "max_riders": 31,
      "audio": "Sound by JBL 40mm speaker, wideband HD",
      "talk_time_hours": 13,
      "waterproof": "IP67",
      "features": ["Crash detection", "SOS call", "Natural Voice commands"],
      "release_year": 2023,
      "notes": "Flagship mesh intercom; premium audio quality; most expensive in category",
      "dimensions": {
        "form_factor": "Clip-mount intercom (boom mic, modular)",
        "ease_of_use": "Glove-operable controls; steep learning curve for mesh features",
        "sound": "Crisp highs, balanced mids; wideband advantage over competitors",
        "intercom": "31-rider mesh at full reliability; universal BT bridging to non-mesh",
        "quality": "Renowned for durability; crashes common in motorsports, Pro known for surviving impacts",
        "price_competitiveness": "Premium ($449 street); justified by audio + mesh reliability but undercut by Sena lifetime warranty",
        "safety": "IMU-based crash detection; SOS triggers auto-call to selected contact",
        "warranty": "3-year hardware (standard); no lifetime option",
        "battery": "13h talk time (industry average); lower than Sena 60S EVO (27h)",
        "integration": "Cardo Connect app for rider profiles and group management; integrates with helmets (Beyond, Venture)",
        "ai_assistant": "Natural Voice command set (commands only, no generative AI)",
        "crossbrand": "Bluetooth bridge mode lets other brands pair; not reciprocal (Sena mesh can't add Cardo as easily)"
      }
    }
  ],

  "strengths": [
    "DMC mesh reliability — wins head-to-head tests for range and stability",
    "Crash detection and SOS — most proven implementation vs competitors",
    "Wideband audio partnership (Sound by JBL) — perceived as superior to Bose by some reviewers",
    "First-mover advantage in integrated helmets (Beyond, Venture)"
  ],

  "weaknesses": [
    "Pricing strategy backfired: 2025 hikes + no mesh under $360 opened flank",
    "Mesh-Boost delayed 18+ months past November 2024 announcement; erodes free-OTA credibility",
    "Support reputation: Trustpilot complaints about slow warranty handling, web-form-only funnel",
    "Battery life underperforms vs Sena flagships (13h vs 27h); lower in specs"
  ],

  "recent_news": [
    {
      "date": "2026-07-01",
      "headline": "Cardo and Leatt formalize Venture partnership ($799 integrated-mesh MX helmet)",
      "source": "Cardo newsroom",
      "url": "https://..."
    }
  ],

  "social_media": {
    "instagram": {
      "handle": "cardosystems",
      "url": "https://instagram.com/cardosystems",
      "followers": 45000
    },
    "facebook": {
      "handle": "CardoSystems",
      "url": "https://facebook.com/CardoSystems",
      "followers": 32000
    },
    "facebook_group": {
      "name": "Cardo Systems Community",
      "url": "https://facebook.com/groups/1847605508861922",
      "members": 28000
    },
    "youtube": {
      "handle": "CardoSystemsGlobal",
      "url": "https://youtube.com/@CardoSystemsGlobal",
      "subscribers": 18000
    },
    "recent_posts": [
      {
        "date": "2026-07-05",
        "platform": "Instagram",
        "summary": "Beyond GT/GTS helmet launch teaser with focus on audio quality and mesh reliability",
        "url": "https://instagram.com/cardosystems"
      }
    ]
  },

  "press_coverage": {
    "overall_tone": "positive|mixed|negative",
    "reviews": [
      {
        "outlet": "MCN (Motorcycle News)",
        "product": "Packtalk Pro",
        "date": "2026-05-15",
        "rating": "4/5",
        "verdict": "Best overall for group riding reliability; premium audio worth the price",
        "url": "https://..."
      }
    ]
  },

  "firmware_updates": [
    {
      "date": "2026-07-02",
      "product": "Packtalk Pro",
      "type": "firmware|app",
      "version": "4.7.2",
      "title": "Mesh-Boost feature rollout phase 3 (31-rider support)",
      "changes": [
        "31-rider mesh group support",
        "Enhanced noise cancellation",
        "Battery optimization on idle"
      ],
      "url": "https://cardosystems.com/support/firmware",
      "source": "Official release notes"
    }
  ],

  "current_software": {
    "app_name": "Cardo Ride",
    "app_ios_version": "8.14.1",
    "app_android_version": "8.14.0",
    "app_last_updated": "2026-07-05",
    "notes": "Rebranded from 'Cardo Connect' as of May 2026; added reWind ride recap and account linking"
  },

  "product_firmware": [
    {
      "product": "Packtalk Pro",
      "firmware_version": "4.7.2",
      "firmware_last_updated": "2026-07-02",
      "release_notes_url": "https://cardosystems.com/support/packtalk-pro-firmware",
      "user_manual_url": "https://cardosystems.com/manuals/packtalk-pro-en.pdf",
      "support_url": "https://cardosystems.com/support/contact"
    }
  ],

  "customer_feedback": [
    {
      "date": "2026-07-08",
      "source": "Reddit",
      "forum": "r/motorcyclegear",
      "product": "Packtalk Pro",
      "sentiment": "negative",
      "topic": "Battery life complaint",
      "summary": "User reports 13h talk time is barely enough for weekend tours; Sena 60S EVO at 27h is much better",
      "url": "https://reddit.com/r/motorcyclegear/comments/..."
    }
  ],

  "sources": [
    "https://cardosystems.com",
    "https://revzilla.com/cardo",
    "Official Instagram, Facebook, YouTube",
    "r/motorcyclegear subreddit",
    "Motorcycle press (MCN, webBikeWorld, FortNine, Bennetts)"
  ],

  "amazon_pricing": {
    "fetched_at": "2026-07-13T15:04:57.126245+00:00",
    "domain": "US",
    "products": [
      {
        "asin": "B09MQ7R1D8",
        "title": "Cardo Packtalk Pro...",
        "current": { "amazon": 98.95, "new": 98.95, "buybox": null, "list_price": null },
        "sales_rank": 733,
        "rating": 4.5,
        "review_count": 1203,
        "keepa_url": "https://keepa.com/#!product/1-B09MQ7R1D8"
      }
    ]
  }
}
```

`amazon_pricing` only appears if `KEEPA_API_KEY` was configured when the research agent last ran for that brand, and only covers ASINs listed for that brand in `research/keepa_asins.json`. If Keepa isn't configured, this key is simply absent or stale (left as whatever it was on the last successful fetch) — `build.py` and the dashboard handle that gracefully.

### Field Definitions

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `competitor` | string | ✓ | Brand name: Cardo, Sena, ASMAX, Reso |
| `website` | URL | ✓ | Official brand website |
| `company.founded` | integer | ✓ | Year (e.g., 2003) |
| `company.hq` | string | ✓ | Headquarters location (e.g., "Israel") |
| `company.description` | string | ✓ | 1-2 sentence brand overview |
| `products[].name` | string | ✓ | Exact product name (e.g., "Packtalk Pro") |
| `products[].tier` | enum | ✓ | flagship, mid, entry (for communicators only; leave null for helmets) |
| `products[].category` | enum | ✓ | communicator, smart_helmet (determines tier display) |
| `products[].msrp_usd` | float | | Manufacturer suggested retail price (USD) |
| `products[].street_price_usd` | float | ✓ | Typical street price (RevZilla, Amazon, etc.) |
| `products[].intercom_tech` | string | ✓ | Type and capabilities (e.g., "DMC Gen2 mesh (31 riders), auto-pairing") |
| `products[].range_km` | float | ✓ | Claimed range in kilometers (verify vs real-world) |
| `products[].max_riders` | integer | ✓ | Maximum group size supported |
| `products[].audio` | string | ✓ | Speaker description and partnerships (e.g., "Sound by JBL 40mm") |
| `products[].talk_time_hours` | float | ✓ | Talk time on single charge |
| `products[].waterproof` | string | ✓ | IP rating (IP67, IPX7, etc.) or "waterproof/splash-resistant" |
| `products[].features[]` | string[] | ✓ | List of key features |
| `products[].release_year` | integer | ✓ | Year product was released |
| `products[].dimensions` | object | ✓ | See dimensions schema below |
| `recent_news[]` | object[] | ✓ | News items must be YYYY-MM-DD and have real URLs |
| `social_media.recent_posts[]` | object[] | ✓ | Social posts: must be real, never fabricate |
| `press_coverage.reviews[]` | object[] | ✓ | Press reviews with dates and outlets |
| `firmware_updates[]` | object[] | | Firmware/app release history |
| `current_software` | object | ✓ | Current companion app version |
| `product_firmware[]` | object[] | | Per-product current firmware state |
| `customer_feedback[]` | object[] | ✓ | Real customer posts from forums (Reddit, Facebook Group, Instagram) |
| `amazon_pricing` | object | | Keepa snapshot for this brand's tracked ASINs; absent/stale if `KEEPA_API_KEY` isn't configured |

### Product Dimensions Object

```json
"dimensions": {
  "form_factor": "Clip-mount intercom (boom mic, modular) | Face-mounted helmet comm | ...",
  "ease_of_use": "Glove-operable controls; steep learning curve for mesh features",
  "sound": "Crisp highs, balanced mids; wideband advantage over competitors",
  "intercom": "31-rider mesh at full reliability; universal BT bridging to non-mesh",
  "quality": "Renowned for durability; crashes common in motorsports, Pro known for surviving impacts",
  "price_competitiveness": "Premium ($449 street); justified by audio + mesh reliability",
  "safety": "IMU-based crash detection; SOS triggers auto-call",
  "warranty": "3-year hardware; no lifetime option",
  "battery": "13h talk time (industry average); lower than Sena 60S EVO (27h)",
  "integration": "Cardo Connect app for rider profiles; integrates with helmets",
  "ai_assistant": "Natural Voice command set (commands only, no generative AI)",
  "crossbrand": "Bluetooth bridge mode; not reciprocal with Sena mesh"
}
```

All 16 dimensions must be present for every product (used in dashboard Battles tab).

---

## gap_analysis.json

Pricing and feature gaps specific to Cardo. Updated manually or by analyst.

```json
{
  "generated": "2026-07-08",
  "analyst": "Strategy team",
  "summary": "Cardo is losing on price and losing on features in two critical segments",
  
  "pricing_gaps": [
    {
      "title": "No mesh under $360 (CRITICAL)",
      "cardo_solution": "Packtalk Neo $359.95",
      "competitor_benchmarks": [
        { "brand": "Sena", "product": "Spider X Slim", "price": 299, "features": "Mesh, Bose audio, lifetime warranty" },
        { "brand": "ASMAX", "product": "S1", "price": 89.99, "features": "Mesh, offline AI, IPX7" }
      ],
      "market_size": "Entry buyers (under $350) where brand loyalty is formed",
      "urgency": "HIGH — both competitors launched sub-$300 mesh in June 2026"
    }
  ],
  
  "feature_gaps": [
    {
      "title": "No lifetime warranty (Flagship)",
      "cardo": "Packtalk Pro: 3-year",
      "competitor_benchmark": "Sena 60S EVO: Limited lifetime",
      "customer_impact": "Reduces perceived value; Sena uses warranty as headline differentiator",
      "urgency": "HIGH"
    },
    {
      "title": "Cellular intercom unmarketed",
      "cardo": "VoIP cellular inside Mesh-Boost, not called out in marketing",
      "competitor_benchmark": "Sena Wave: Named product, app, friends groups, press coverage",
      "customer_impact": "Riders credit competitors for a feature Cardo also ships",
      "urgency": "HIGH"
    }
  ]
}
```

### gap_analysis.json Schema

| Field | Type | Required |
|-------|------|----------|
| `generated` | string (YYYY-MM-DD) | ✓ |
| `summary` | string | ✓ |
| `pricing_gaps[]` | object[] | ✓ |
| `feature_gaps[]` | object[] | ✓ |
| `pricing_gaps[].title` | string | ✓ |
| `pricing_gaps[].cardo_solution` | string | ✓ |
| `pricing_gaps[].competitor_benchmarks[]` | object[] | ✓ |
| `feature_gaps[].urgency` | enum: HIGH, MEDIUM, LOW | ✓ |

---

## battles.json

Head-to-head product comparisons with 16-dimension rating matrices.

```json
{
  "generated": "2026-07-05",
  "battles": [
    {
      "name": "High-End Mesh: Packtalk Pro vs Sena 60X vs ASMAX Future 1 Pro",
      "segment": "Flagship mesh communicators",
      "exec_summary": "Cardo leads on audio; Sena leads on warranty and battery",
      
      "ratings": {
        "models": ["Packtalk Pro", "Sena 60X", "ASMAX Future 1 Pro"],
        "rows": [
          {
            "dimension": "Form factor",
            "scores": ["y", "y", "y"],
            "values": ["Clip-mount boom", "Modular clip", "Clip-mount boom"]
          },
          {
            "dimension": "Ease of Use",
            "scores": ["y", "p", "soso"],
            "values": ["Intuitive controls", "Joystick at speed", "Limited glove control"]
          },
          {
            "dimension": "Sound",
            "scores": ["y", "y", "p"],
            "values": ["JBL 40mm wideband", "Bose audio", "Tuned drivers"]
          },
          ... (16 total)
        ]
      }
    }
  ]
}
```

### Score Legend
- `y` = Yes/Leads
- `p` = Partial/Parity
- `soso` = So-so
- `n` = No/Missing

---

## product_insights.json

Strategic analysis regenerated daily by Product Expert agent.

```json
{
  "generated": "2026-07-08",
  "analyst_note": "Cardo still owns the thing that matters most — group intercom reliability — and reviewers keep handing it 'best overall' titles. But I see a company harvesting that reputation rather than defending it.",
  
  "executive_summary": "Cardo enters H2 2026 as the review-consensus quality leader with a genuinely differentiated smart-helmet story (Beyond, Venture), but its pricing umbrella is under coordinated attack.",
  
  "market_pulse": [
    {
      "date": "2026-07-03",
      "brand": "Cardo",
      "development": "Beyond GT/GTS helmets go on sale at RevZilla with widespread size out-of-stock",
      "implication": "Early demand for smart-helmet bet looks real; execution risk is now inventory, not interest"
    }
  ],
  
  "gaps": [
    {
      "title": "No mesh below $360",
      "severity": "critical",
      "category": "product",
      "description": "Cardo's cheapest motorcycle mesh unit is the Packtalk Neo at $359.95; every competitor now sells mesh in the $90-300 window.",
      "evidence": [
        "Packtalk Neo $359.95 (Cardo's mesh floor) vs Sena Spider X Slim $299 (Bose, lifetime warranty) vs ASMAX S1 $89.99",
        "r/motorcyclegear (June 2026): 'insane that cardos cost more than actual helmets'",
        "Reddit sentiment: $250-350 buyers who want mesh cannot buy Cardo at all"
      ],
      "customer_signal": "r/motorcyclegear consensus: budget mesh riders switching to ASMAX and Reso",
      "competitor_benchmark": "Sena Spider X Slim: $299 mesh-only with Bose audio and lifetime warranty"
    }
  ],
  
  "recommendations": [
    {
      "priority": 1,
      "horizon": "now",
      "title": "Close the sub-$300 mesh hole with a de-contented DMC unit",
      "rationale": "This is the critical gap and it is widening: Spider X Slim landed in June and ASMAX/Reso own everything below it.",
      "expected_impact": "Defends the volume segment where first-time buyers form loyalty; blunts Spider X Slim before it accumulates reviews",
      "effort": "high",
      "addresses_gaps": ["No mesh below $360"]
    }
  ],
  
  "watchlist": [
    {
      "item": "ASMAX US retail arrival (F1 Pro Max on Amazon US)",
      "why": "ASMAX's 2025 flagship generation ($155-269) is only Asia-only; US arrival would legitimize budget tier",
      "trigger": "F1 Pro Max listed on Amazon US or first tier-1 review (FortNine/webBikeWorld)"
    }
  ]
}
```

### product_insights.json Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `generated` | string (YYYY-MM-DD) | ✓ | Date analysis was generated |
| `analyst_note` | string | ✓ | 2-4 sentence opinionated brief |
| `executive_summary` | string | ✓ | 2-3 paragraphs strategic analysis |
| `market_pulse[]` | object[] | ✓ | 6-10 recent competitive moves |
| `gaps[]` | object[] | ✓ | 6-9 evidence-grounded gaps |
| `recommendations[]` | object[] | ✓ | 5-8 priority-ordered actions |
| `watchlist[]` | object[] | ✓ | 3-5 signals to monitor |
| `gaps[].severity` | enum | ✓ | critical, high, medium, low |
| `gaps[].category` | enum | ✓ | product, pricing, software, gtm, support |
| `recommendations[].horizon` | enum | ✓ | now, next, later |
| `recommendations[].effort` | enum | ✓ | low, medium, high |

---

## Data Validation Rules

All JSON files must pass these checks:

### Universal Rules
- ✓ Valid JSON (no syntax errors)
- ✓ No smart quotes (use straight ASCII `"`, not `"` or `"`)
- ✓ All dates in `YYYY-MM-DD` format
- ✓ All URLs are real and working (verify with a browser — there's no scraping-tool-specific verification step)
- ✓ No hardcoded personal data (API keys, passwords, private emails)

### Brand JSON Rules
- ✓ All products[] have exact matching names (used in dashboard filter)
- ✓ All dimensions[] keys present for every product (16 total)
- ✓ No duplicate entries in recent_news, press_coverage, firmware_updates, customer_feedback (check date + topic)
- ✓ recent_posts[] URLs point to brand's official account (Instagram profile URL, not post permalink) for IG/FB/TikTok

### gap_analysis.json Rules
- ✓ Evidence array populated with real numbers and quotes
- ✓ Urgency set to HIGH, MEDIUM, or LOW
- ✓ Competitor benchmarks reference real products from other brands' research JSONs

### battles.json Rules
- ✓ All ratings[] rows have exactly 3 scores and 3 values (one per model)
- ✓ Scores are y, p, soso, or n (never blank)
- ✓ Values match products in research JSONs

### product_insights.json Rules
- ✓ Every claim grounded in research data (no invented numbers)
- ✓ Evidence array has real quotes or price comparisons from research files
- ✓ Recommendations map to gap titles in gaps[] array
- ✓ market_pulse entries newest first

---

## Verification Checklist

Before committing research changes:

```bash
# Check JSON syntax for each file
python3 -c "import json; json.load(open('research/cardo.json'))"
python3 -c "import json; json.load(open('research/gap_analysis.json'))"
python3 -c "import json; json.load(open('research/battles.json'))"
python3 -c "import json; json.load(open('research/product_insights.json'))"

# Build the dashboard
python3 build.py

# Validate the rendered HTML's embedded JavaScript
sed -n '/<script>/,/<\/script>/p' dashboard.html | sed '1d;$d' > /tmp/check.js
node -c /tmp/check.js

# If all pass, commit
git add research/*.json dashboard.html index.html
git commit -m "Daily data refresh $(date +%Y-%m-%d)"
```

---

**Last updated:** September 29, 2026
