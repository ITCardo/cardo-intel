"""Optional: let Claude file NEW records under the existing thematic families.

Only fetched records are sent (title, applicant, class codes). Claude does not search and makes
no infringement or validity statement. Disabled unless --families is passed and ANTHROPIC_API_KEY is set.
"""
from __future__ import annotations

import json
import os


def assign_families(records: list[dict], families: list[dict], log=print, client=None) -> int:
    todo = [r for r in records if r["flags"].get("new") and not r.get("topic")]
    if not todo or not families:
        return 0
    if client is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            log("families: ANTHROPIC_API_KEY not set, skipped")
            return 0
        import anthropic
        client = anthropic.Anthropic(api_key=key)
    fam_txt = "\n".join(f"- {f['id']}: {f['name']}" for f in families)
    done = 0
    for i in range(0, len(todo), 20):
        batch = todo[i:i + 20]
        items = [{"id": r["id"], "title": r["title"], "applicants": r["applicants"][:2], "classes": r["cpc"][:4]}
                 for r in batch]
        prompt = (
            "File each patent record under one of these families, or answer \"none\" if it fits no family.\n"
            f"{fam_txt}\n\nRecords (JSON):\n{json.dumps(items, ensure_ascii=False)}\n\n"
            "Answer with JSON only: a list of {\"id\": ..., \"family\": <family id or \"none\">, \"note\": <max 12 words>}. "
            "Use only the data given. Do not make claims about infringement or validity.")
        try:
            msg = client.messages.create(model="claude-sonnet-5-5", max_tokens=2000,
                                         messages=[{"role": "user", "content": prompt}])
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
            text = text[text.find("["): text.rfind("]") + 1]
            answers = {a["id"]: a for a in json.loads(text)}
        except Exception as exc:  # noqa: BLE001 - never let this fail the crawl
            log(f"families: batch skipped ({type(exc).__name__})")
            continue
        names = {f["id"]: f["name"] for f in families}
        for r in batch:
            a = answers.get(r["id"])
            if a and a.get("family") in names:
                r["topic"], r["topic_note"] = names[a["family"]], "assigned by Claude: " + str(a.get("note", ""))[:100]
                done += 1
    return done
