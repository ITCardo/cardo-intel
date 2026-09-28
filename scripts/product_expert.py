#!/usr/bin/env python3
"""
Product Expert agent - synthesizes strategic insights from all research data.
Regenerates product_insights.json from scratch daily.
"""
import sys
import json
import pathlib
from datetime import datetime
from anthropic import Anthropic

client = Anthropic()

def load_brand_slugs() -> list:
    cfg = json.loads(pathlib.Path("research/brands.json").read_text())
    return [b["slug"] for b in cfg["brands"]]

def load_all_research() -> dict:
    """Load all research files for synthesis."""
    data = {}

    for brand in load_brand_slugs():
        path = pathlib.Path(f"research/{brand}.json")
        if path.exists():
            data[brand] = json.loads(path.read_text())

    # Load analysis files
    gap_path = pathlib.Path("research/gap_analysis.json")
    if gap_path.exists():
        data["gap_analysis"] = json.loads(gap_path.read_text())

    battles_path = pathlib.Path("research/battles.json")
    if battles_path.exists():
        data["battles"] = json.loads(battles_path.read_text())

    return data

def run_product_expert(all_research: dict) -> dict:
    """
    Run Product Expert agent - reads all research and regenerates insights.
    """

    # Prepare research summary for Claude (truncated for token limits)
    def brand_summary(brand: str) -> dict:
        brand_data = all_research.get(brand) or {}
        products = brand_data.get("products") or []
        recent_news = brand_data.get("recent_news") or []
        press_reviews = (brand_data.get("press_coverage") or {}).get("reviews") or []
        customer_feedback = brand_data.get("customer_feedback") or []
        return {
            "products_count": len(products),
            "recent_news_count": len(recent_news),
            "press_reviews_count": len(press_reviews),
            "customer_feedback_count": len(customer_feedback),
            "latest_news": recent_news[:3],
            "latest_feedback": customer_feedback[:3],
        }

    slugs = load_brand_slugs()
    research_summary = {
        brand: brand_summary(brand)
        for brand in slugs
    }
    brand_names_cfg = json.loads(pathlib.Path("research/brands.json").read_text())["brands"]
    brand_names = [b["name"] for b in brand_names_cfg]

    prompt = f"""You are an experienced senior product manager analyzing competitive intelligence for Cardo Systems.

TODAY'S DATE: {datetime.now().strftime('%Y-%m-%d')}

RESEARCH DATA SUMMARY:
{json.dumps(research_summary, indent=2)}

FULL RESEARCH AVAILABLE: {", ".join(brand_names)} brand data with products, news, press, social, customer feedback
GAP ANALYSIS AVAILABLE: Strategic gaps identified
BATTLES AVAILABLE: Head-to-head comparisons

TASK: Regenerate research/product_insights.json from scratch based on TODAY'S research data.

Your analysis should:
1. Lead with an opinionated analyst brief (2-4 sentences) on Cardo's competitive position
2. Provide a 2-3 paragraph executive summary
3. Identify 6-10 recent market-pulse items (most strategic recent moves from competitors and Cardo)
4. Highlight 6-9 evidence-grounded product gaps Cardo faces
5. Recommend 5-8 prioritized actions (now/next/later) with effort levels
6. Flag 3-5 key signals to watch that could shift the competitive landscape

CRITICAL GUIDELINES:
- Be opinionated and position-taking, not wishy-washy
- Every claim must be grounded in the research data provided
- Never invent numbers, quotes, or competitive moves
- Use real product names, real dates, real prices from the data
- Evidence array should cite real data points (e.g., "Sena Spider X Slim $299", "Reddit: battery life complaints")
- Recommendations should map to specific gaps you identified
- Watchlist items should have concrete triggers for action

OUTPUT FORMAT: Return ONLY valid JSON (no markdown) with this exact structure:
{{
  "generated": "YYYY-MM-DD",
  "analyst_note": "2-4 sentence opinionated brief",
  "executive_summary": "2-3 paragraphs of strategic analysis",
  "market_pulse": [
    {{"date": "YYYY-MM-DD", "brand": "{'|'.join(brand_names)}", "development": "what happened", "implication": "why it matters"}},
    ...
  ],
  "gaps": [
    {{
      "title": "Gap title",
      "severity": "critical|high|medium|low",
      "category": "product|pricing|software|gtm|support",
      "description": "2-3 sentences",
      "evidence": ["evidence 1", "evidence 2", ...],
      "customer_signal": "real customer quote or null",
      "competitor_benchmark": "how competitor handles this"
    }},
    ...
  ],
  "recommendations": [
    {{
      "priority": 1,
      "horizon": "now|next|later",
      "title": "Action title",
      "rationale": "why this matters",
      "expected_impact": "what changes if done",
      "effort": "low|medium|high",
      "addresses_gaps": ["Gap title 1", "Gap title 2"]
    }},
    ...
  ],
  "watchlist": [
    {{
      "item": "specific move to monitor",
      "why": "strategic importance",
      "trigger": "concrete event that would signal threat"
    }},
    ...
  ]
}}

Use straight ASCII quotes. Validate the JSON before outputting."""

    print("🔄 Calling Claude API for Product Expert analysis...")

    full_response = ""
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            full_response += text
            if len(full_response) % 500 == 0:
                print(".", end="", flush=True)
        stop_reason = stream.get_final_message().stop_reason

    print()

    if stop_reason == "max_tokens":
        print(f"⚠️ Response was cut off at max_tokens ({len(full_response)} chars received)")

    # Parse JSON from response. Use raw_decode instead of find('{')/rfind('}')
    # so trailing text after a valid JSON object (commentary, etc.) doesn't
    # break the parse - raw_decode reads exactly one JSON value and ignores
    # whatever follows it.
    try:
        json_start = full_response.find('{')
        if json_start >= 0:
            insights, _ = json.JSONDecoder().raw_decode(full_response, json_start)

            # Ensure generated date is today
            insights["generated"] = datetime.now().strftime('%Y-%m-%d')

            print("✅ Parsed product insights from Claude")
            return insights
        else:
            print("⚠️ No JSON found in response")
            return None
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse insights JSON: {e}")
        return None

def save_insights(insights: dict) -> None:
    """Save product insights JSON."""
    path = pathlib.Path("research/product_insights.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Validate JSON
    json.dumps(insights, ensure_ascii=False)
    path.write_text(json.dumps(insights, indent=2, ensure_ascii=False))
    print("✅ Saved research/product_insights.json")

def validate_insights(insights: dict) -> bool:
    """Validate insights structure."""
    required_keys = ["generated", "analyst_note", "executive_summary", "market_pulse",
                     "gaps", "recommendations", "watchlist"]

    missing = [k for k in required_keys if k not in insights]
    if missing:
        print(f"⚠️ Warning: insights missing keys: {missing}")
        return False

    # Check arrays have content
    if not isinstance(insights.get("market_pulse"), list) or len(insights["market_pulse"]) < 3:
        print("⚠️ Warning: market_pulse should have 6+ items")

    if not isinstance(insights.get("gaps"), list) or len(insights["gaps"]) < 3:
        print("⚠️ Warning: gaps should have 6+ items")

    if not isinstance(insights.get("recommendations"), list) or len(insights["recommendations"]) < 3:
        print("⚠️ Warning: recommendations should have 5+ items")

    return True

def main():
    print(f"\n{'='*60}")
    print("Product Expert Agent")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}\n")

    try:
        # Load all research
        print("📚 Loading research data...")
        all_research = load_all_research()

        if not all_research:
            print("⚠️ No research data found, skipping Product Expert")
            return

        # Run analysis
        insights = run_product_expert(all_research)

        if insights:
            # Validate
            if validate_insights(insights):
                # Save
                save_insights(insights)
                print(f"\n✅ Product Expert completed successfully")
                print(f"   Generated: {insights.get('generated')}")
                print(f"   Market pulse items: {len(insights.get('market_pulse') or [])}")
                print(f"   Gaps identified: {len(insights.get('gaps') or [])}")
                print(f"   Recommendations: {len(insights.get('recommendations') or [])}")
            else:
                print("\n⚠️ Insights have validation issues but saved anyway")
                save_insights(insights)
        else:
            print("\n❌ Failed to generate insights")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error in Product Expert: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
