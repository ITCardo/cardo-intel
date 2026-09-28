#!/usr/bin/env python3
"""
Apify Social Listener - scrapes REAL Facebook Group and Instagram posts via
Apify actors, then uses Claude only to classify/summarize that real data
(sentiment, topic, product match) - never to invent it.

This replaces the Facebook/Instagram portions of social_media_listener.py,
which had no actual web access and was generating plausible-looking but
unverifiable content. Reddit coverage in social_media_listener.py is
unaffected by this script.

Requires the APIFY_API_TOKEN environment variable (GitHub secret in CI).
"""
import os
import sys
import json
import pathlib
import urllib.request
import urllib.error
from datetime import datetime
from anthropic import Anthropic

client = Anthropic()
APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN")

def _load_brand_sources() -> dict:
    """Build the {slug: {facebook_groups, instagram}} map from research/brands.json
    so adding a new brand to scrape never requires touching this script."""
    cfg = json.loads(pathlib.Path("research/brands.json").read_text())
    return {
        b["slug"]: {
            "facebook_groups": b.get("facebook_groups", []),
            "instagram": f"https://www.instagram.com/{b['instagram']}/" if b.get("instagram") else None,
        }
        for b in cfg["brands"]
    }

BRAND_SOURCES = _load_brand_sources()

# Window wider than the daily cadence so a missed/failed run doesn't create a gap;
# dedup by URL makes re-scraping the same posts harmless.
POSTS_NEWER_THAN = "3 days"

def call_apify_actor(actor_id: str, actor_input: dict, timeout_secs: int = 120) -> list:
    """Run an Apify actor synchronously via REST API and return dataset items."""
    if not APIFY_TOKEN:
        raise RuntimeError("APIFY_API_TOKEN environment variable not set")
    encoded_actor = actor_id.replace("/", "~")
    url = f"https://api.apify.com/v2/acts/{encoded_actor}/run-sync-get-dataset-items?token={APIFY_TOKEN}&timeout={timeout_secs}"
    req = urllib.request.Request(
        url,
        data=json.dumps(actor_input).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_secs + 30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"⚠️ Apify actor {actor_id} HTTP error {e.code}: {e.read().decode('utf-8')[:300]}")
        return []
    except Exception as e:
        print(f"⚠️ Apify actor {actor_id} failed: {e}")
        return []

def scrape_facebook_groups(brand: str) -> list:
    groups = BRAND_SOURCES[brand]["facebook_groups"]
    if not groups:
        return []
    print(f"🔄 Scraping {len(groups)} Facebook group(s) for {brand.upper()}...")
    items = call_apify_actor(
        "apify/facebook-groups-scraper",
        {
            "startUrls": [{"url": g["url"]} for g in groups],
            "resultsLimit": 25,
            "onlyPostsNewerThan": POSTS_NEWER_THAN,
        },
    )
    print(f"   → {len(items)} raw Facebook posts")
    return items

def scrape_instagram(brand: str) -> list:
    profile_url = BRAND_SOURCES[brand]["instagram"]
    if not profile_url:
        return []
    print(f"🔄 Scraping Instagram for {brand.upper()}...")
    items = call_apify_actor(
        "apify/instagram-scraper",
        {
            "directUrls": [profile_url],
            "resultsType": "posts",
            "resultsLimit": 15,
            "onlyPostsNewerThan": POSTS_NEWER_THAN,
        },
    )
    print(f"   → {len(items)} raw Instagram posts")
    return items

def classify_feedback_batch(brand: str, fb_posts: list, product_names: list) -> list:
    """Ask Claude to classify REAL Facebook posts (sentiment/topic/product) - never invent content."""
    if not fb_posts:
        return []

    trimmed = [
        {
            "text": (p.get("text") or "")[:600],
            "date": (p.get("time") or "")[:10],
            "url": p.get("url"),
            "group": p.get("groupTitle"),
        }
        for p in fb_posts
        if p.get("text") and p.get("url")
    ]
    if not trimmed:
        return []

    prompt = f"""You are classifying REAL customer Facebook posts about {brand.upper()} motorcycle communicators. Every post below was actually scraped - do not invent, alter, or embellish any of it.

KNOWN PRODUCT NAMES: {json.dumps(product_names)}

POSTS:
{json.dumps(trimmed, indent=2)}

For EACH post, return a classification object. Skip posts that are pure spam/ads/off-topic with no product relevance.

OUTPUT: Return ONLY a JSON array, one object per relevant post:
[
  {{
    "date": "YYYY-MM-DD (from the post's date field, unchanged)",
    "source": "Facebook Group",
    "forum": "(the group field, unchanged)",
    "product": "exact match from KNOWN PRODUCT NAMES, or General if unclear/not product-specific",
    "sentiment": "positive|negative|mixed|neutral",
    "topic": "2-5 word label",
    "summary": "1-2 sentence factual paraphrase of the ACTUAL post text - no invented details",
    "url": "(the url field, unchanged)"
  }}
]

Return ONLY the JSON array, no markdown."""

    print(f"🔄 Classifying {len(trimmed)} real posts for {brand.upper()}...")
    full_response = ""
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            full_response += text

    try:
        start = full_response.find("[")
        classified, _ = json.JSONDecoder().raw_decode(full_response, start)
        print(f"✅ Classified {len(classified)} posts for {brand}")
        return classified
    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️ Failed to parse classification for {brand}: {e}")
        return []

def merge_customer_feedback(brand: str, new_items: list) -> None:
    path = pathlib.Path(f"research/{brand}.json")
    data = json.loads(path.read_text())
    existing = data.get("customer_feedback", [])
    existing_urls = {item.get("url") for item in existing if item.get("url")}

    added = 0
    for item in new_items:
        if item.get("url") and item["url"] not in existing_urls:
            existing.append(item)
            existing_urls.add(item["url"])
            added += 1

    if added == 0:
        print(f"ℹ️  No new Facebook feedback for {brand} (all duplicates)")
        return

    data["customer_feedback"] = existing
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"✅ Added {added} new Facebook feedback items to {brand}.json")

def merge_instagram_posts(brand: str, ig_posts: list) -> None:
    if not ig_posts:
        return
    path = pathlib.Path(f"research/{brand}.json")
    data = json.loads(path.read_text())
    social = data.setdefault("social_media", {})
    existing = social.get("recent_posts", [])
    existing_urls = {item.get("url") for item in existing if item.get("url")}

    added = 0
    for p in ig_posts:
        url = p.get("url")
        if not url or url in existing_urls:
            continue
        existing.append({
            "date": (p.get("timestamp") or "")[:10],
            "platform": "Instagram",
            "summary": (p.get("caption") or "")[:300],
            "url": url,
        })
        existing_urls.add(url)
        added += 1

    if added == 0:
        print(f"ℹ️  No new Instagram posts for {brand} (all duplicates)")
        return

    social["recent_posts"] = existing
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"✅ Added {added} new Instagram posts to {brand}.json")

def main():
    print(f"\n{'='*60}")
    print("Apify Social Listener Agent")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}\n")

    if not APIFY_TOKEN:
        print("❌ APIFY_API_TOKEN not set - skipping (this is a hard requirement, not optional)")
        sys.exit(1)

    for brand in BRAND_SOURCES:
        try:
            path = pathlib.Path(f"research/{brand}.json")
            data = json.loads(path.read_text())
            product_names = [p["name"] for p in data.get("products", [])]

            fb_posts = scrape_facebook_groups(brand)
            classified = classify_feedback_batch(brand, fb_posts, product_names)
            merge_customer_feedback(brand, classified)

            ig_posts = scrape_instagram(brand)
            merge_instagram_posts(brand, ig_posts)

        except Exception as e:
            print(f"❌ Error processing {brand}: {e}")
            # Continue with other brands rather than failing the whole run
            continue

    print("\n✅ Apify Social Listener completed")

if __name__ == "__main__":
    main()
