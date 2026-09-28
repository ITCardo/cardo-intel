#!/usr/bin/env python3
"""
Research agent script for daily competitive intelligence refresh.
Calls Claude API directly to gather and synthesize research data.

Design note: Claude is asked to report ONLY new/changed items (a delta),
not to regenerate the entire existing dataset. The delta is merged into
the existing JSON in Python. This keeps output size proportional to daily
changes rather than to the accumulated dataset size, which would otherwise
eventually exceed any max_tokens ceiling as the data grows. It also removes
the failure mode where a truncated "full regeneration" silently overwrites
good data with an incomplete one.
"""
import sys
import json
import pathlib
from datetime import datetime
from anthropic import Anthropic

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from keepa_scan import fetch_brand_pricing  # noqa: E402  (needs sys.path tweak above)

# Initialize Anthropic client
client = Anthropic()

# Server-side web search tool: without this, the model has no way to actually
# browse the web and can only report from training data / the existing JSON
# passed in the prompt. max_uses caps searches per call as a cost guardrail.
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 8}

def load_brand_registry() -> dict:
    """Load research/brands.json -> {slug: {name, website, handles}}. Adding a
    new brand to research is just adding an entry there, no code change here."""
    cfg = json.loads(pathlib.Path("research/brands.json").read_text())
    return {
        b["slug"]: {
            "name": b["name"],
            "website": b["website"],
            "handles": {
                "instagram": b.get("instagram"),
                "facebook": b.get("facebook"),
                "youtube": b.get("youtube"),
            },
        }
        for b in cfg["brands"]
    }

def load_existing_json(brand: str) -> dict:
    """Load existing research JSON for a brand."""
    path = pathlib.Path(f"research/{brand}.json")
    if path.exists():
        return json.loads(path.read_text())
    return {}

def save_research_json(brand: str, data: dict) -> None:
    """Save research JSON with proper formatting."""
    path = pathlib.Path(f"research/{brand}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Validate JSON before saving
    json.dumps(data)  # This will raise if invalid
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"✅ Saved research/{brand}.json")

def _dedupe_key(item: dict, *fields: str) -> str:
    """Build a dedupe key from the first non-empty field found."""
    for f in fields:
        v = item.get(f)
        if v:
            return f"{f}:{v}"
    return json.dumps(item, sort_keys=True)

def _merge_list_by_name(existing: list, updates: list, name_field: str = "name") -> list:
    """Replace items matching by name (case-insensitive), append the rest."""
    result = list(existing)
    for item in updates:
        key = str(item.get(name_field, "")).strip().lower()
        matched = False
        for i, existing_item in enumerate(result):
            if str(existing_item.get(name_field, "")).strip().lower() == key and key:
                result[i] = item
                matched = True
                break
        if not matched:
            result.append(item)
    return result

def _append_deduped(existing: list, new_items: list, *dedupe_fields: str) -> list:
    """Append new_items to existing, skipping items that already exist."""
    existing_keys = {_dedupe_key(item, *dedupe_fields) for item in existing}
    result = list(existing)
    for item in new_items:
        key = _dedupe_key(item, *dedupe_fields)
        if key not in existing_keys:
            result.append(item)
            existing_keys.add(key)
    return result

def merge_delta(existing_data: dict, delta: dict) -> dict:
    """Merge a delta (new/changed items only) into the existing research JSON."""
    result = json.loads(json.dumps(existing_data))  # deep copy

    if delta.get("new_or_updated_products"):
        result["products"] = _merge_list_by_name(
            result.get("products", []), delta["new_or_updated_products"]
        )

    if delta.get("product_firmware_updates"):
        result["product_firmware"] = _merge_list_by_name(
            result.get("product_firmware", []), delta["product_firmware_updates"], name_field="product"
        )

    if delta.get("new_recent_news"):
        result["recent_news"] = _append_deduped(
            result.get("recent_news", []), delta["new_recent_news"], "url", "headline"
        )

    if delta.get("new_firmware_updates"):
        result["firmware_updates"] = _append_deduped(
            result.get("firmware_updates", []), delta["new_firmware_updates"], "url", "title"
        )

    if delta.get("new_sources"):
        existing_sources = set(result.get("sources", []))
        result["sources"] = result.get("sources", []) + [
            s for s in delta["new_sources"] if s not in existing_sources
        ]

    press_coverage = result.setdefault("press_coverage", {})
    if delta.get("new_press_reviews"):
        press_coverage["reviews"] = _append_deduped(
            press_coverage.get("reviews", []), delta["new_press_reviews"], "url", "outlet"
        )
    if delta.get("new_awards"):
        press_coverage["awards"] = _append_deduped(
            press_coverage.get("awards", []), delta["new_awards"], "url", "title", "name"
        )
    if delta.get("press_coverage_summary"):
        press_coverage["summary"] = delta["press_coverage_summary"]

    social_media = result.setdefault("social_media", {})
    if delta.get("new_social_posts"):
        social_media["recent_posts"] = _append_deduped(
            social_media.get("recent_posts", []), delta["new_social_posts"], "url", "summary"
        )
    if delta.get("social_media_summary"):
        social_media["summary"] = delta["social_media_summary"]

    if delta.get("strengths"):
        result["strengths"] = delta["strengths"]
    if delta.get("weaknesses"):
        result["weaknesses"] = delta["weaknesses"]
    if delta.get("current_software"):
        result["current_software"] = {**result.get("current_software", {}), **delta["current_software"]}
    if delta.get("company"):
        result["company"] = {**result.get("company", {}), **delta["company"]}

    return result

def run_research_agent(brand: str) -> dict:
    """
    Run research agent for a specific brand using Claude API.
    Returns the merged, updated research JSON.
    """
    existing_data = load_existing_json(brand)
    details = load_brand_registry().get(brand, {})
    existing_product_names = [p.get("name") for p in existing_data.get("products", [])]

    prompt = f"""You are a competitive intelligence analyst researching {details.get('name', brand)}.

TASK: Report ONLY what is NEW or CHANGED for {brand} since the existing data below. Do NOT repeat unchanged data - you are producing a small delta, not a full regeneration.

EXISTING DATA (for context only - do not repeat unchanged parts of this in your response): {json.dumps(existing_data, indent=2)}

EXISTING PRODUCT NAMES (for matching): {json.dumps(existing_product_names)}

TODAY'S DATE: {datetime.now().strftime('%Y-%m-%d')}

RESEARCH REQUIREMENTS:
1. Check {details.get('website')} for new product launches and pricing changes
2. Search for recent press coverage (motorcycle magazines: MCN, webBikeWorld, RevZilla, FortNine, Bennetts, RideApart)
3. Look for firmware/app updates via release notes and app stores
4. Check social media: Instagram @{details.get('handles', {}).get('instagram')}, YouTube, Reddit r/motorcyclegear
5. Verify real customer feedback (no fabrication)

OUTPUT FORMAT: Return ONLY valid JSON (no markdown, no explanation) with this shape. Omit any key entirely if there is nothing new/changed for it - do not include empty arrays or nulls for unchanged sections:
{{
  "new_or_updated_products": [ <full product object, same schema as existing products, including full 16-dimension capability matrix> ],
  "product_firmware_updates": [ <full product_firmware object, matched by "product" name> ],
  "new_recent_news": [ <news item, same schema as existing recent_news items> ],
  "new_firmware_updates": [ <firmware item, same schema as existing firmware_updates items> ],
  "new_press_reviews": [ <review item, same schema as existing press_coverage.reviews items> ],
  "new_awards": [ <award item, same schema as existing press_coverage.awards items> ],
  "new_social_posts": [ <post item, same schema as existing social_media.recent_posts items> ],
  "new_sources": [ "url", ... ],
  "strengths": [ ... ],
  "weaknesses": [ ... ],
  "current_software": {{ ... }},
  "company": {{ ... }},
  "social_media_summary": "...",
  "press_coverage_summary": "..."
}}

MATCHING RULES:
- "new_or_updated_products": if the product's "name" matches an existing product name (case-insensitive), it REPLACES that product entirely (so include the full object, not just changed fields). If the name doesn't match any existing product, it's added as new.
- "strengths"/"weaknesses": only include if something genuinely changed; if included, provide the complete replacement list (these are short).
- All other "new_*" arrays are appended to the existing lists - only include items that are not already present in the existing data.

PRODUCT CATEGORY CLASSIFICATION:
Every product in "new_or_updated_products" must include a "category" field, one of:
- "smart_helmet" - a full helmet with integrated communication system
- "headphones" - an audio-only accessory (over-ear or earmuff-style) that pairs with a separate communicator unit rather than being a standalone communicator itself (e.g. Cardo Packtalk Edgephones, ASMAX F1 RidePhones, Sena Tufftalk line). If it's marketed primarily as hearing protection or off-helmet audio rather than as a full intercom system, classify it here even if it has its own Bluetooth/mesh chip.
- "outdoor" - a communicator designed for non-motorcycle activities (ski/snowboard, cycling, skating, general outdoor/strap-helmet use) even if it uses the same underlying Bluetooth/mesh tech as the moto lineup, e.g. Cardo Packtalk Outdoor, Sena Snowtalk 2, Sena BiKom 20, Sena pi. If it's marketed at a specific non-moto sport or as a general multi-sport clip-on unit, classify it here.
- "communicator" - the default: a standalone Bluetooth/mesh intercom unit, whether helmet-mounted or clamp-on
Check {details.get('website')}'s full product catalog (not just what's in existing data) for any headphones-category or outdoor-category products not yet tracked - this brand may have off-helmet audio accessories, ski/cycling-specific units, or industrial/multi-sport sub-brands worth capturing.

PRODUCT USAGE:
Every product in "new_or_updated_products" should include a "usage" field: a short string describing what activity it's designed for, e.g. "Motorcycle" (the default for the main lineup), "Ski, snowboard", "Cycling", "Cycling, skating, multi-sport". Base this on how the brand actually markets the product, not a guess - check the product page's stated use case.

PRODUCT PAGE URL:
Every product in "new_or_updated_products" should include a "url" field: the direct link to that specific product's page on the brand's own official site (not a retailer, not a category/collection page). If you cannot find or verify the exact product page URL, use null rather than guessing - never fabricate a URL. When updating an existing product for another reason, include its correct "url" too if the existing entry is missing one.

CRITICAL RULES:
- Do NOT invent products, prices, or customer feedback
- Do NOT create fake URLs - verify everything is real
- Use null for unknown values rather than guessing
- All dates in YYYY-MM-DD format
- No smart quotes - use straight ASCII only
- If nothing is new or changed at all, return {{}}

Return the delta JSON now."""

    print(f"🔄 Calling Claude API for {brand.upper()} research...")

    # Use streaming for longer outputs
    full_response = ""
    with client.messages.stream(
        model="claude-sonnet-5-5",
        max_tokens=8000,
        tools=[WEB_SEARCH_TOOL],
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            full_response += text
            # Print progress dots
            if len(full_response) % 500 == 0:
                print(".", end="", flush=True)
        stop_reason = stream.get_final_message().stop_reason

    print()  # Newline after dots

    if stop_reason == "max_tokens":
        print(f"⚠️ Response for {brand} was cut off at max_tokens ({len(full_response)} chars received)")

    # Parse the JSON response. raw_decode reads exactly one JSON value and
    # ignores any trailing text, unlike find('{')/rfind('}') which breaks
    # if the response has commentary after the JSON object.
    try:
        json_start = full_response.find('{')
        if json_start >= 0:
            delta, _ = json.JSONDecoder().raw_decode(full_response, json_start)
            print(f"✅ Parsed {brand} delta from Claude: {list(delta.keys()) or '(no changes)'}")
        else:
            print(f"⚠️ No JSON found in Claude response for {brand}, treating as no changes")
            delta = {}
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse JSON delta for {brand}: {e}")
        print(f"   Treating as no changes - existing data preserved")
        delta = {}

    merged = merge_delta(existing_data, delta)

    # Safety guardrail: a merge should only ever add data, never lose it.
    # If any growing collection shrank, something went wrong upstream -
    # refuse to save rather than silently overwriting good data with less.
    for key in ["products", "recent_news", "firmware_updates", "sources", "product_firmware"]:
        before = len(existing_data.get(key, []) or [])
        after = len(merged.get(key, []) or [])
        if after < before:
            raise ValueError(
                f"Refusing to save {brand}: merged '{key}' has {after} items, "
                f"existing data had {before}. This should never happen with delta merging - "
                f"aborting to avoid data loss."
            )

    return merged

def validate_research_data(brand: str, data: dict) -> bool:
    """Validate research JSON structure."""
    required_keys = ["competitor", "website", "company", "products", "strengths",
                     "weaknesses", "recent_news", "social_media", "press_coverage"]

    missing = [k for k in required_keys if k not in data]
    if missing:
        print(f"⚠️ Warning: {brand} JSON missing keys: {missing}")
        return False

    if not isinstance(data.get("products"), list):
        print(f"⚠️ Warning: {brand} products is not a list")
        return False

    # Validate that JSON is serializable
    try:
        json.dumps(data, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️ Warning: {brand} JSON is not serializable: {e}")
        return False

def main():
    valid_brands = list(load_brand_registry().keys())
    if len(sys.argv) < 2:
        print(f"Usage: python research_agent.py <brand> ({'|'.join(valid_brands)})")
        sys.exit(1)

    brand = sys.argv[1].lower()
    if brand not in valid_brands:
        print(f"Invalid brand: {brand}. Valid brands (from research/brands.json): {valid_brands}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Research Agent: {brand.upper()}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}\n")

    try:
        # Run research
        updated_data = run_research_agent(brand)

        # Amazon pricing (Keepa) — each brand's agent fetches its own product
        # pricing/BSR/rating as part of its normal run. Never fatal: skips
        # cleanly if KEEPA_API_KEY isn't configured or the brand has no ASINs.
        print(f"Fetching Amazon pricing for {brand} via Keepa...")
        pricing = fetch_brand_pricing(brand)
        if pricing:
            updated_data["amazon_pricing"] = pricing

        # Validate
        if validate_research_data(brand, updated_data):
            # Save
            save_research_json(brand, updated_data)
            print(f"\n✅ {brand.upper()} research agent completed successfully")
        else:
            print(f"\n⚠️ {brand.upper()} research has validation issues but was saved")
            save_research_json(brand, updated_data)

    except Exception as e:
        print(f"\n❌ Error in {brand.upper()} research agent: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
