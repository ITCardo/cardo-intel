"""Product families: Yanis's own grouping of patent records by subject (and priority date).

A "family" here is NOT the patent family number. It is a numbered product/subject family such as
"1 Wireless intercom - group pairing". The list lives in config.json ("families") and grows over time.

Order of decisions for each patent family (all records that share the BigQuery/EPO family id are one unit):
  1. config "family_overrides"            (your manual correction, always wins)
  2. the "family" column of the known list (your own grouping of the numbers you track)
  3. the previous run                      (so a decision is made once and then kept)
  3b. config "family_seed"                 (starting grouping Claude set up from titles; review it)
  4. Claude: put it into an existing family when it fits, otherwise create the next numbered family
     and name it. Only title, applicants and class codes are sent. No search, no legal statement.

Everything Claude decides is labelled "inferred". The registry (all families, including new ones)
and the per-brand map are written to ip_results.json and read back on the next run.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date

MODEL = "claude-sonnet-5-5"
BATCH = 25


# ------------------------------------------------------------------ registry
def build_registry(config_families: list[dict], previous: list[dict] | None) -> list[dict]:
    """Seed families from config; add families that earlier runs created. Config names win."""
    reg: dict[int, dict] = {}
    for f in previous or []:
        try:
            reg[int(f["id"])] = {"id": int(f["id"]), "name": str(f["name"]), "created": f.get("created", ""), "by": f.get("by", "claude")}
        except (KeyError, ValueError, TypeError):
            continue
    for f in config_families or []:
        fid = int(re.sub(r"\D", "", str(f["id"])) or 0)
        if fid:
            reg[fid] = {"id": fid, "name": f["name"], "created": "", "by": "you"}
    return [reg[k] for k in sorted(reg)]


def _find_family(value, registry) -> int | None:
    """Known-list or override value: a number, 'F3', or the family name."""
    if value in (None, ""):
        return None
    s = str(value).strip()
    ids = {f["id"] for f in registry}
    m = re.fullmatch(r"[Ff]?\s*(\d+)", s)
    if m and int(m.group(1)) in ids:
        return int(m.group(1))
    low = re.sub(r"\s+", " ", s.casefold())
    for f in registry:
        n = re.sub(r"\s+", " ", f["name"].casefold())
        if low == n or low.endswith(n) or n.endswith(low) and len(low) > 8:
            return f["id"]
    return None


# ------------------------------------------------------------------ units
def unit_key(rec: dict) -> str:
    return rec["family_id"] if rec.get("family_id") else "rec:" + rec["id"]


def _ascii_ratio(s: str) -> float:
    return sum(c.isascii() for c in s) / max(len(s), 1)


def _unit_info(key: str, recs: list[dict]) -> dict:
    titles = []
    for r in sorted(recs, key=lambda r: (-_ascii_ratio(r.get("title", "")), len(r.get("title", "")))):
        t = r.get("title", "")
        if t and t not in titles:
            titles.append(t)
    cpcs = []
    for r in recs:
        for c in r.get("cpc", []):
            if c not in cpcs:
                cpcs.append(c)
    prio = sorted(p for p in (r.get("priority_date") for r in recs) if p)
    apps = []
    for r in recs:
        for a in r.get("applicants", []):
            if a not in apps:
                apps.append(a)
    return {"key": key, "titles": titles[:3], "classes": cpcs[:6], "priority": prio[0] if prio else "",
            "applicants": apps[:2], "records": len(recs)}


# ------------------------------------------------------------------ main entry
def assign(brands_out: list[dict], registry: list[dict], previous_maps: dict | None, overrides: dict | None,
           run_date: str | None = None, log=print, client=None, seed: dict | None = None, use_claude: bool = True) -> dict:
    """Fill topic_id / topic / topic_note on every record. Returns {"registry": [...], "created": [ids], "claude": n}."""
    run_date = run_date or date.today().isoformat()
    previous_maps = previous_maps or {}
    overrides = {str(k): v for k, v in (overrides or {}).items()}
    seed = {str(k): v for k, v in (seed or {}).items()}
    names = {f["id"]: f["name"] for f in registry}
    created: list[int] = []
    pending: list[tuple[dict, str, list[dict]]] = []      # (brand, key, records)

    for b in brands_out:
        fmap = {}
        units: dict[str, list[dict]] = {}
        for r in b["records"]:
            units.setdefault(unit_key(r), []).append(r)
        prev = previous_maps.get(b["slug"]) or {}
        for key, recs in units.items():
            fid, by, note = None, "", ""
            for cand in [key] + [r["id"] for r in recs] + [r["number"] for r in recs]:
                if str(cand) in overrides:
                    fid = _find_family(overrides[str(cand)], registry)
                    if fid:
                        by, note = "you", "your correction"
                        break
            if not fid:
                for r in recs:                          # known list: crawler put the row's family text in topic
                    fid = _find_family(r.get("topic"), registry)
                    if fid:
                        by, note = "you", "your known list"
                        break
            if not fid and key in prev and int(prev[key].get("id", 0)) in names:
                fid, by, note = int(prev[key]["id"]), prev[key].get("by", "claude"), prev[key].get("note", "")
            if not fid and str(key) in seed:
                fid = _find_family(seed[str(key)], registry)
                if fid:
                    by, note = "seed", "starting grouping from the titles, please review"
            if fid:
                fmap[key] = {"id": fid, "by": by, "note": note}
            else:
                pending.append((b, key, recs))
        b["family_map"] = fmap

    claude_done = 0
    if pending and not use_claude:
        log(f"families: {len(pending)} patent family(ies) not in any product family yet (Claude filing is off)")
    elif pending:
        if client is None and os.environ.get("ANTHROPIC_API_KEY"):
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        if client is None:
            log("families: ANTHROPIC_API_KEY not set, new patent families stay unassigned")
        else:
            for i in range(0, len(pending), BATCH):
                batch = pending[i:i + BATCH]
                answers = _ask(client, registry, names, batch, log)
                for (b, key, recs), a in zip(batch, answers):
                    if a is None:
                        continue
                    fid = a["family"]
                    if isinstance(fid, str) and fid.startswith("new:"):
                        label = fid[4:]
                        nm = a["new_names"].get(label, "").strip()
                        if not nm:
                            continue
                        found = next((f["id"] for f in registry if f["name"].casefold() == nm.casefold()), None)
                        if found:
                            fid = found
                        else:
                            fid = max([f["id"] for f in registry] + [0]) + 1
                            registry.append({"id": fid, "name": nm, "created": run_date, "by": "claude"})
                            names[fid] = nm
                            created.append(fid)
                    if fid in names:
                        b["family_map"][key] = {"id": fid, "by": "claude", "note": a.get("note", "")}
                        claude_done += 1

    for b in brands_out:
        fmap = b.get("family_map", {})
        for r in b["records"]:
            m = fmap.get(unit_key(r))
            if m and m["id"] in names:
                r["topic_id"], r["topic"] = m["id"], names[m["id"]]
                who = {"you": "Your grouping: ", "seed": "Starting grouping (set from titles, review): "}.get(m["by"], "Inferred by Claude from the title and class codes: ")
                r["topic_note"] = who + (m.get("note") or "")
            else:
                r["topic_id"], r["topic"], r["topic_note"] = 0, "", ""
    registry.sort(key=lambda f: f["id"])
    return {"registry": registry, "created": created, "claude": claude_done}


def _ask(client, registry, names, batch, log) -> list:
    """One batch. Returns a list aligned with batch: {"family": id | "new:LABEL", "note", "new_names"} or None."""
    fam_txt = "\n".join(f"{f['id']}: {f['name']}" for f in registry)
    units = [_unit_info(key, recs) | {"brand": b["name"]} for b, key, recs in batch]
    prompt = (
        "You file patent families of competitors (motorcycle and helmet communication, intercom and headset makers) "
        "into the product/subject families used by a competitive-intelligence team. A family groups patent families by subject "
        "and priority date. Existing families:\n" + fam_txt + "\n\n"
        "Rules: put each unit into an existing family when it fits. Only if it clearly fits none, create a new family: answer "
        "\"new:<label>\" and give the new family a short English name in the same style as the existing names "
        "(for example 'Helmet camera systems & mounts'). Units that share a new subject must use the same label. "
        "Prefer existing families; do not create a new family for a small variation. Use only the data given. "
        "Do not make claims about infringement or validity.\n\n"
        "Units (JSON):\n" + json.dumps(units, ensure_ascii=False) + "\n\n"
        "Answer with JSON only: {\"assignments\": [{\"key\": <unit key>, \"family\": <existing id as a number or \"new:<label>\">, "
        "\"note\": <max 12 words>}], \"new_families\": {\"<label>\": \"<name>\"}}")
    try:
        msg = client.messages.create(model=MODEL, max_tokens=4000, messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        data = json.loads(text[text.find("{"): text.rfind("}") + 1])
        by_key = {str(a["key"]): a for a in data.get("assignments", [])}
        new_names = {str(k): str(v) for k, v in (data.get("new_families") or {}).items()}
    except Exception as exc:  # noqa: BLE001 - never let this fail the crawl
        log(f"families: batch skipped ({type(exc).__name__})")
        return [None] * len(batch)
    out = []
    for _, key, _r in batch:
        a = by_key.get(str(key))
        if not a:
            out.append(None)
            continue
        fam = a.get("family")
        if isinstance(fam, str) and re.fullmatch(r"\d+", fam.strip()):
            fam = int(fam)
        if isinstance(fam, int) and fam in names:
            out.append({"family": fam, "note": str(a.get("note", ""))[:100], "new_names": new_names})
        elif isinstance(fam, str) and fam.startswith("new:") and new_names.get(fam[4:]):
            out.append({"family": fam, "note": str(a.get("note", ""))[:100], "new_names": new_names})
        else:
            out.append(None)
    return out
