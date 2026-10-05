# Competitive Intelligence Platform — Product Specification

**Version:** 2.0 (functional & user-experience specification)
**Date:** July 15, 2026
**Status:** Draft for review
**Reference product:** Cardo Competitive Intelligence dashboard (live at cardo-intel.cardosystems.com, login required)

---

## 1. What this product is

The Competitive Intelligence Platform keeps a company permanently up to date on its competitors — automatically.

The user picks the competitors to watch. From then on, the platform continuously researches them: new product launches, pricing moves, feature changes, firmware and app releases, press coverage, social media activity, and what real customers are saying in public forums and groups. Everything it finds is organized into a single, always-current, interactive dashboard that product managers, marketers, and executives can open any morning and trust.

Three promises define the product:

1. **Always current.** The data refreshes on a schedule the admin sets. Every screen shows exactly when it was last updated, and every piece of data shows when it was collected.
2. **Always sourced.** Every fact links to where it came from — the product page, the news article, the actual customer post. Opinions and analyst-style judgments are visibly labeled as such. Nothing is ever invented.
3. **Owned by the team, not by engineers.** Adding a competitor, a product line, a new market category, or a new data source is something an admin does in minutes through the interface — never a request to a developer.

This specification is reverse-engineered from a working single-company implementation (Cardo Systems tracking Sena, ASMAX, and Reso in the motorcycle intercom market) and generalizes it into a product any organization can configure for its own market.

---

## 2. Who uses it

| Role | Who they are | What they can do |
|---|---|---|
| **Viewer** | Product managers, marketers, sales, executives | Open the dashboard, filter and explore everything, follow source links, export views. Cannot change any data. |
| **Editor (Analyst)** | The person accountable for data quality — often a product marketing manager or analyst | Everything a Viewer can, plus: review and approve the system's newly found data, correct or reject items, add manual entries, request a fresh look at a specific competitor or product. |
| **Admin** | The workspace owner's delegate | Everything an Editor can, plus: add/remove competitors, manage categories and taxonomies, connect data sources, set the refresh schedule, manage users and budgets. |
| **Owner** | Accountable for the account | Everything an Admin can, plus: billing, publishing visibility (public vs. company-only), data retention decisions. |

The permission model is simple to explain: **viewing is broad, changing is narrow, configuring is narrower, and nothing is deleted destructively — ever.** Retired competitors and discontinued products are archived, not erased.

---

## 3. Core concepts (the user's mental model)

- **Competitor** — a company being tracked. Has a profile (who they are, positioning, strengths/weaknesses), a product catalog, and live feeds (news, social, press, software releases, customer feedback).
- **Product** — an item in a competitor's (or your own) catalog, with specs, pricing, category, and usage. Your own company is modeled the same way, so every view is comparative.
- **Category** — the product taxonomy for your market. In the reference product: communicators, smart helmets, headphones, outdoor devices. Admins define these; the dashboard's filters, badges, and charts follow automatically.
- **Usage** — what a product is for (motorcycle, ski, cycling…). A second, orthogonal filter dimension, because markets increasingly cross activity boundaries.
- **Dimension** — an axis products are judged on (sound quality, range, battery life, ease of use, warranty…). Admins maintain the dimension list per category. Battles and comparisons are built from these.
- **Battle** — a head-to-head: one of your products versus its direct rivals in a segment, scored across every dimension, with a written executive summary.
- **Gap** — a specific place where you trail (or lead) the field: a missing feature, a price disadvantage, with severity and a recommendation.
- **Insight** — the synthesized layer: executive summary, market pulse, recommendations, and a watchlist, regenerated after every refresh.
- **Source** — a place the platform collects from: official sites, Amazon pricing, Reddit communities, public Facebook groups, Instagram profiles, news feeds. Admins attach sources per competitor.
- **Refresh (Run)** — one scheduled or manual collection cycle. Everything new lands in a review area before it appears on the dashboard (depending on policy — see §7).

---

## 4. The Dashboard (the viewer experience)

The dashboard is one continuously updated site with ten tabs. It opens fast, works on any modern browser including mobile, and requires zero training: everything is filterable, sortable, and clickable where you'd expect.

### 4.0 Global experience

- **Header:** product title, a subtitle naming the tracked competitors, and a **full "last updated" timestamp** shown in the viewer's own timezone (e.g., "last updated July 14, 2026 at 10:04 AM (America/New_York)").
- **Personalization, remembered per user:**
  - **Style switcher** — six visual themes: Dark (default), Bright (pure-black text on white for maximum print-like readability), Midnight, Sepia, Nord, and High Contrast (accessibility-oriented). The choice persists across visits.
  - **Text size** — A− / A+ controls step the entire dashboard between 70% and 160%.
- **Layout:** content is left-aligned and uses the full width of any screen, from laptop to ultrawide. Wide tables scroll inside their own cards; the page itself never scrolls horizontally. Charts cap their own width so data stays visually dense instead of stretching into sparseness.
- **Source links everywhere:** any fact with a real origin carries a small ↗ that opens the source in a new tab — the competitor's product page, the news article, the actual Reddit thread or Facebook post. This is the product's trust signature and appears on every tab.
- **Trust labels:** sourced facts and analyst inferences (e.g., a strengths/weaknesses judgment) are visually distinct, so a reader always knows whether they're looking at evidence or interpretation.
- **Per-tab freshness:** each tab footer states when its data was last collected and whether it has been human-reviewed.

### 4.1 Overview

The one-screen morning briefing.

- **Brand cards** — one per company: logo/color, HQ and founding, positioning summary, product count, price range, and a link out to their site.
- **Competitive positioning table** — each brand's top strengths (green) and weaknesses (red) side by side.
- **Press & market table** — review counts, award counts, and overall press tone per brand.
- **Recent moves feed** — a single reverse-chronological stream of everything notable across all competitors (launches, price cuts, partnerships, firmware releases), filterable by brand chips, every item dated and linked to its source.

### 4.2 Products

The full market catalog in one table.

- **Filters:** brand chips, category dropdown, tier dropdown, usage dropdown, release-year dropdown, capability toggles (e.g., "mesh only"), and free-text search across names and features.
- **Columns:** product, brand, tier, usage, MSRP, street price, communication tech, range, group size, talk time, waterproofing, year — all sortable by clicking headers. A live counter shows how many products match the current filters.
- **Expandable rows:** clicking a product reveals its full detail — feature list, notes, per-dimension details, and a "View product page ↗" link to the manufacturer's own site.
- **Category badges** (smart helmet, headphones, outdoor) keep non-comparable items visually distinct in mixed views.

### 4.3 Battles

Segment-by-segment head-to-head decks — the tab a PM opens before a roadmap debate.

- A **chip row of segments** (e.g., "Entry Bluetooth," "High-end Mesh flagship," "Off-helmet audio"); selecting one loads that battle.
- Each battle shows your **hero product versus its direct rivals** as columns, scored **GOOD / SO-SO / BAD** across every dimension the category defines (sound, range, battery, waterproofing, warranty…), with a notes column explaining each verdict.
- **Rank / Value toggle:** flip every cell from the verdict to the underlying number (riders, km, hours, price) and back.
- **Interactive columns:** every rival column has a swap control (⇄) to replace it with any other rated product, a **+** to add another column (up to a sensible max), and ✕ to remove one — so users compose the exact comparison they need on the fly.
- Each battle opens with a written **executive summary** ("The entry tier is defended by distribution and brand, not by product").
- Hovering a dimension name reveals its sub-criteria.

### 4.4 Model Compare

A spec-sheet builder.

- Pick up to 7 products from any brands (preset picks offered for common matchups).
- A dense spec-by-spec table: tier/type, usage, prices, tech, range, riders, audio, battery, waterproofing, warranty, feature checklists, and a product-page link per column.

### 4.5 Pricing

Where the market's money story lives.

- A **price landscape chart**: each brand is a column of points, every product plotted at its *effective price* (verified street price where known, otherwise MSRP). Shapes encode tier (▲ flagship, ■ mid, ● entry) — readable even in monochrome. Hovering any point shows the product, effective price, MSRP, and tier. Toggles include or exclude non-comparable categories (helmets, headphones, outdoor).
- **Price ladders** — computed cards such as "cheapest mesh-capable unit per brand," updating automatically as prices change.
- **Price history** — each product's dated price observations as a sparkline, so a discount that quietly became permanent is visible.

### 4.6 Gap Analysis

The self-critical tab: where do we trail?

- **Feature gaps table** — feature, our status (missing / behind / partial / parity / leads), competitor note, severity (critical → low), and a recommendation per row. Filterable by severity and status; sortable by any column.
- **Pricing gaps** — segment-level price disadvantages, stated plainly.
- **Advantages** — the mirror image: where we lead and should press.

### 4.7 Social & Press

- **Per-brand social cards** — follower counts and activity across Instagram, Facebook, TikTok, YouTube, each linked out.
- **Recent posts** — actual recent social posts per brand, with dates, text, and links to the posts themselves.
- **Press & reviews feed** — searchable stream of reviews and coverage, with outlet, date, tone, and links.

### 4.8 Software & Firmware

Release velocity as a competitive signal.

- Per-brand cards: current app version, last update date, support link, and firmware baseline.
- A filterable release table — every firmware/app release, per product, with dates and changelog summaries. A brand that hasn't shipped an update in a year is visible at a glance.

### 4.9 Voice of the Customer

Real customers, real posts, zero invention.

- A stream of individual customer discussions from public communities (Reddit, public Facebook groups), each with: date, source community, product concerned, sentiment (positive / negative / mixed / neutral), a topic label, a 1–3 sentence faithful summary, and — non-negotiably — **a link to the actual post**.
- Filterable by brand, sentiment, source, and product; searchable by text.
- Sentiment distribution bars per brand give the at-a-glance mood.

### 4.10 Product Insights

The synthesized executive layer, regenerated each refresh.

- **Executive summary** — a few paragraphs of "what changed and what it means."
- **Market pulse** — a dated, sortable feed of significant developments with implications ("Sena 60X is out of stock everywhere → demand outstripping supply in the flagship tier"), each linked to evidence. Default-sorted newest first; sortable by date or brand from the header.
- **Recommendations** — numbered, horizon-tagged (NOW / NEXT / LATER) action items.
- **Watchlist** — the specific things to watch before next refresh.

### 4.11 What changed (changelog view)

A "since you last looked" digest: everything added or changed in the most recent refresh — new products found, prices that moved, notable posts, new gaps — in one scannable list. This is the single most-requested capability from reference-product users.

---

## 5. The Admin Console (the configuration experience)

A separate, always-authenticated area. Its design goal: **every operation a growing intelligence practice needs, doable by a non-technical admin in minutes.**

### 5.1 Onboarding a new competitor

A guided wizard:

1. **Identify** — name, website, brand color (suggested automatically from their site), logo, regions.
2. **Seed sources** — the wizard proposes discoverable sources (their official product pages, their Instagram, their subreddit presence, Amazon listings) and lets the admin confirm, remove, or add others (e.g., paste the URLs of the two public Facebook groups where their owners congregate).
3. **Bootstrap** — the platform runs an initial deep-research pass and presents the draft profile and product catalog *for review* — nothing appears on the dashboard until an editor approves it.
4. **Done** — the brand appears across every dashboard tab with its own color, filters, and feeds, indistinguishable from competitors configured on day one.

Archiving a competitor is one click: it disappears from the dashboard, collection stops, and history is retained.

### 5.2 Managing products

- **Approve, don't type:** the normal flow is that the platform *finds* new products and proposes them; an editor reviews the proposal (name, specs, price, category, source link), fixes anything, and approves. One click, done.
- **Manual add/edit** is always available through the same form — for a launch the system hasn't seen yet or internal knowledge. Manually entered facts are labeled as such.
- **Duplicate merge:** when the same product arrives under two spellings, an editor merges them once; the platform remembers the alias forever.
- **Discontinue, don't delete:** products leave the catalog by being marked discontinued (with date and reason), preserving history and price trails.

### 5.3 Managing the taxonomy

- **Categories:** create, rename, retire. Each category carries its display behavior — badge label and color, whether tiers apply (helmets don't; communicators do), whether it appears in the pricing chart by default, whether it participates in computed ladders. Change it here, and every tab follows.
- **Usage tags:** a simple managed vocabulary (motorcycle, ski, cycling, multi-sport…).
- **Dimensions:** the judgment axes per category. Add "Crash detection" as a dimension and it appears in future battles; retire one and it stops appearing without erasing past scores.

### 5.4 Managing sources and the schedule

- **Source registry:** every connected source in one list — type, what it covers, its refresh cost, when it last ran, and its health (working / failing / stale). Adding a source is choosing a type (official site, Amazon pricing, Reddit community, public Facebook group, Instagram profile, news feed) and filling in its specifics.
- **Schedule:** one refresh cadence for the workspace — default weekly, admin-chosen day and hour, displayed unambiguously ("Mondays 10:00 AM America/New_York"). A **Run now** button exists for the day a competitor drops a surprise launch, for the whole workspace or a single competitor.
- **Budgets:** monthly spending caps for research and data collection, with a live meter, an alert at 80%, and graceful degradation (lowest-priority sources pause first) rather than surprise overruns. Spend is visible per refresh, per source, and per competitor.

### 5.5 The review queue

The editor's inbox, and the reason the dashboard can be trusted.

- After each refresh, everything new waits here, grouped by competitor and type, presented as **readable before/after diffs**: "Sena: 2 new products, 14 customer posts, 3 price changes, 1 product discontinued."
- **Approve / edit / reject** per item, with bulk-approve for low-risk classes.
- **Auto-approval policy** is a dial the admin sets per data class, not a switch:

| Data class | Default policy |
|---|---|
| News, social posts, customer feedback (all with source links) | Auto-approved, listed in a digest |
| Price changes within normal bounds | Auto-approved, digest |
| Suspicious changes (a price that moved 40%+, a spec that jumped implausibly) | Held for review, flagged |
| New products, discontinuations, spec changes | Held for review |
| Strengths/weaknesses, battle verdicts, gap severities, recommendations | Held for review |

- **Staleness nudges:** items waiting too long, and dashboard data not re-verified within a threshold, are flagged — stale intelligence presented as fresh is treated as a defect.
- Rejections require a reason (wrong product, bad summary, duplicate, suspect source); these feed a monthly quality review.

### 5.6 Users and access

- Users are invited by email and sign in with the company's standard login (SSO). Roles per §2, changeable by admins, deny-by-default.
- An access page answers "who can see and change what" at a glance — the artifact a security review asks for first.

---

## 6. Trust, security, and governance (as the user experiences them)

This product handles competitively sensitive analysis and publishes claims about other companies. The experience is designed so that trust is *visible*, not assumed.

### 6.1 Publishing visibility

Three modes, chosen by the Owner, always displayed in the admin console:

- **Company-only (recommended default):** the dashboard requires company sign-in.
- **Secret link:** accessible to anyone holding an unguessable URL — clearly labeled in the console as low-assurance, for board packets and partner shares.
- **Public:** open web. An explicit Owner decision with a confirmation that spells out the consequence: *your competitors will be able to read your analysis of them.*

Additionally, admins can mark specific tabs (typically Gap Analysis and Product Insights — the strategy layer) as **internal-only**. The platform then maintains two versions of the dashboard from the same data: a shareable one without those tabs, and the full internal one.

### 6.2 Provenance and honesty rules

- Every factual item shows its source link and collection date. Items with no external source exist only when a human editor entered them, and say so.
- **The platform never fabricates.** Customer feedback, social posts, and news exist in the product only if the actual post/article was really retrieved; the link is the proof, and the reader can always click it. (This rule exists because the reference product's early version *did* once present plausible-looking invented forum posts — discovered, removed, and designed against permanently.)
- Analyst-style judgments (strengths, weaknesses, battle verdicts, severities, recommendations) are labeled as interpretation and pass human review before appearing.

### 6.3 Accountability

- **Every change is attributable.** For any item on the dashboard, an editor can see: when it arrived, from which source, in which refresh, who approved it, and every edit since.
- **Everything is reversible.** Any published state can be rolled back in minutes. Nothing is ever hard-deleted; archives preserve history.
- **A refresh history page** lists every run: when, what was collected, what it cost, what was approved and by whom — the audit trail, readable by admins without asking anyone technical.

### 6.4 Responsible collection

- The platform collects **public information only**: public pages, public groups, licensed data services. It never logs into competitor properties, never bypasses access controls, and never impersonates anyone.
- Customer voices are summarized respectfully: the product stores the issue, not the person — no harvesting of user identities beyond what the public link itself contains.
- Published feeds carry summaries plus links, not wholesale copies of articles or posts.
- The console can produce, at any time, a plain-language **"What we collect and from where"** document generated from the actual source registry — the answer to the legal team's first question, always current.

### 6.5 Data quality as a feature

- A periodic **quality report** to editors: what was added, what was flagged, which sources are failing, which links have rotted, which products haven't been re-verified recently.
- Sanity flags on the dashboard itself: a price or spec that changed implausibly displays a review marker until an editor confirms it.

---

## 7. Notifications and sharing

- **Refresh digest** (email/Slack, per-user opt-in): "This week: 3 new products, 2 price cuts, 41 customer posts, 1 new critical gap" — each item deep-linking into the dashboard.
- **Review-needed alerts** to editors when a refresh leaves items waiting, and escalation if they wait too long.
- **Watch alerts (later phase):** follow a specific product or competitor and be notified on price moves or launches.
- **Export:** any table view exports to CSV; any tab prints cleanly (the Bright theme doubles as the print style). Battles and comparisons export as shareable one-pagers.

---

## 8. Accessibility and platform support

- Full keyboard navigability; screen-reader labels on all interactive tables and charts.
- No meaning carried by color alone (tier shapes in the pricing chart, status text alongside every colored badge).
- The High Contrast theme and the 70–160% text scaling are first-class, remembered features.
- Evergreen desktop browsers and mobile; the dashboard is readable on a phone in a hallway before the meeting.

---

## 9. Explicitly out of scope (v1)

- Real-time monitoring or same-day alerting (the cadence is scheduled, weekly by default).
- Collection from paywalled or login-required sources.
- Automated actions in other systems (repricing, ticket creation) — the product informs decisions; it doesn't execute them.
- Multi-language dashboard UI (sources in any language may be summarized in English).

---

## 10. Delivery phases (user-visible capabilities)

**Phase 1 — The trustworthy dashboard.** Everything in §4 for one workspace; configuration by the platform team on the customer's behalf; provenance links and honesty rules fully enforced.

**Phase 2 — Self-service.** The full Admin Console (§5): competitor wizard, product approval flows, taxonomy management, source registry, schedule, budgets, review queue, roles.

**Phase 3 — Trust at scale.** Visibility modes and internal-only tabs, changelog view, refresh digests, price-history sparklines, quality reports, the auto-generated collection disclosure.

**Phase 4 — Reach.** Watch alerts, additional source types (YouTube reviews, app-store reviews, job postings as strategy signals), BI export, multiple workspaces per organization.

---

## 11. Open questions

1. Default visibility: is company-only sign-in acceptable as the hard default, with public publishing requiring an Owner's explicit confirmation? (Recommended: yes.)
2. Who staffs the Editor role in the first customer teams, and how many minutes per week can they give the review queue? (This calibrates the auto-approval defaults in §5.5.)
3. Should the customer's own products be first-class in v1 (recommended — every battle and gap already assumes a "hero"), or is v1 competitors-only?
4. Which two or three additional source types matter most to early customers — YouTube reviews, app-store reviews, or retailer availability tracking?

---

*This specification describes a productized generalization of a working system. Every dashboard behavior in §4 exists and is validated in production today; §5–7 generalize the operating practices that kept that system trustworthy into product features.*
