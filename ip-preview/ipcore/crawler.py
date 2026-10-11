"""Core crawl logic: search, name matching, known-list comparison, status, flags."""
from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import date, datetime, timezone

from . import classify as C
from . import names as N
from .epo import OPSBlocked, OPSError


# ---------------------------------------------------------------- known list
def load_known(path) -> list[dict]:
    """Read the known-records CSV. Only the 'number' column is required."""
    rows = []
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            lines = [ln for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
    except FileNotFoundError:
        return rows
    for r in csv.DictReader(lines):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        if row.get("number"):
            rows.append(row)
    return rows


def status_class(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ("expir", "lapse", "withdr", "abandon", "revok", "ceased", "refus", "invalid")):
        return "expired"
    if any(w in t for w in ("grant", "active", "issued", "registered", "in force")):
        return "granted"
    if any(w in t for w in ("pending", "application", "published", "filed")):
        return "pending"
    return "unknown"


_ORDER = {"pending": 1, "granted": 2, "expired": 3}


def record_id(country, number, kind) -> str:
    return f"{country}{C.canon_docnum(country, number)}{kind}"


# ---------------------------------------------------------------- helpers
def _best_match(rec, brand_names, keywords, excludes, suggested=()):
    """Best name match over all applicants. A match that rests only on a *suggested* (not yet
    approved) name variant is downgraded to 'weak', so a person has to approve it."""
    best, excluded = None, False
    for a in rec.get("applicants", []):
        if N.is_excluded(a, excludes):
            excluded = True
            continue
        m = N.match_name(a, list(brand_names) + list(suggested), keywords, excludes)
        if m and m["name"] in suggested and m["level"] in ("match", "close"):
            m = dict(m, level="weak", reason="matches the suggested variant '" + m["name"] + "', which is not approved yet")
        if m and (best is None or (m["score"], m["level"] == "match") > (best["score"], best["level"] == "match")):
            best = dict(m, applicant=a)
    return best, excluded


def _surname_key(n: str) -> str:
    return re.sub(r"[^a-z0-9㐀-鿿가-힯]", "", n.casefold())


def _topic_hit(rec, prefixes) -> bool:
    codes = [c.split()[0] for c in rec.get("cpc", [])] + [c.split()[0] for c in rec.get("ipc", [])]
    return any(c.startswith(tuple(prefixes)) for c in codes) if prefixes else False


def _docdb_ref(number: str) -> str:
    """'US20150105022A1' -> 'US.20150105022.A1' (only when a kind code is present)."""
    t = re.sub(r"[^0-9A-Za-z]", "", number or "").upper()
    m = re.match(r"^([A-Z]{2})(\d+)([A-Z]\d?)$", t)
    return f"{m.group(1)}.{m.group(2)}.{m.group(3)}" if m else ""


def _pub_number(rec) -> str:
    return f"{rec['country']}{rec['doc_number']}"


# ---------------------------------------------------------------- main per-brand run
def run_brand(brand: dict, cfg: dict, ops, known_rows: list[dict], previous: dict | None,
              today: date | None = None, log=print, bq=None) -> dict:
    today = today or date.today()
    names = list(brand.get("names", [])) + list(brand.get("approved_aliases", []))
    keywords = brand.get("keywords", [])
    excludes = brand.get("exclude", [])
    suggested = brand.get("suggested_variants", [])
    limits = cfg.get("limits", {})
    topic_prefixes = cfg.get("topic_cpc_prefixes", [])
    previous = previous or {}

    diag = {"queries": [], "dropped": Counter(), "excluded": Counter(), "family_calls": 0, "legal_calls": 0,
            "lookup_calls": 0, "errors": []}
    candidates: dict[str, dict] = {}       # rid -> raw record
    sources: dict[str, set] = {}

    def add_raw(raw, source):
        rid = record_id(raw["country"], raw["doc_number"], raw["kind"])
        if rid not in candidates:
            candidates[rid] = raw
        sources.setdefault(rid, set()).add(source)
        return rid

    # ---- pass 1: applicant-name search ----------------------------------
    queries = []
    for n in names + suggested:
        ph = N.search_phrase(n)
        if ph and ph not in queries:
            queries.append(ph)
    cql_list = [f'pa="{q}"' for q in queries] + list(brand.get("extra_cql", []))
    search_hits: set[str] = set()
    if ops is not None:
        for cql in cql_list:
            try:
                recs, total = ops.search(cql, limits.get("max_results_per_query", 300))
                diag["queries"].append({"query": cql, "hits": len(recs), "total": total, "error": ""})
                for r in recs:
                    search_hits.add(add_raw(r, "ops-search"))
            except OPSBlocked as exc:
                diag["queries"].append({"query": cql, "hits": 0, "total": 0, "error": str(exc)})
                diag["errors"].append(str(exc))
                break
            except OPSError as exc:
                diag["queries"].append({"query": cql, "hits": 0, "total": 0, "error": str(exc)})
                diag["errors"].append(str(exc))

    if bq is not None:
        cands = bq.candidates_for(brand)
        diag["queries"].append({"query": "BigQuery: applicant name search (all brands in one query)",
                                "hits": len(cands), "total": len(cands), "error": bq.error})
        if bq.error:
            diag["errors"].append("BigQuery: " + bq.error)
        for r in cands:
            search_hits.add(add_raw(r, "bq-search"))

    # ---- name matching ---------------------------------------------------
    accepted: dict[str, dict] = {}
    review: dict[str, dict] = {}
    pending_close: list[tuple[str, dict]] = []
    for rid in sorted(search_hits):
        raw = candidates[rid]
        m, excluded = _best_match(raw, names, keywords, excludes, suggested)
        if m is None:
            if excluded:
                diag["excluded"][(raw["applicants"] or ["(none)"])[0]] += 1
            else:
                diag["dropped"][(raw["applicants"] or ["(no applicant)"])[0]] += 1
            continue
        if m["level"] == "match":
            accepted[rid] = m
        elif m["level"] == "close":
            pending_close.append((rid, m))
        else:
            review[rid] = dict(m, why=("Only a distinctive word matches. " if "suggested" not in m["reason"] else m["reason"] + ". ") + "A person must approve it.")
    inv_known = {_surname_key(i) for rid in accepted for i in candidates[rid].get("inventors", []) if i}
    for rid, m in pending_close:
        raw = candidates[rid]
        shared = [i for i in raw.get("inventors", []) if _surname_key(i) in inv_known]
        if shared:
            accepted[rid] = dict(m, signal=f"inventor also on accepted records: {shared[0]}")
        elif topic_prefixes and _topic_hit(raw, topic_prefixes):
            accepted[rid] = dict(m, signal="technology class matches the helmet/communication field")
        else:
            review[rid] = dict(m, why="Close name, but no inventor or technology signal. A person must approve it.")

    # ---- pass 2: direct lookup of the known list -------------------------
    known_state = [{"row": r, "rid": None} for r in known_rows]
    all_recs = lambda: candidates.items()  # noqa: E731

    def _row_kind(number):
        t = re.sub(r"[^0-9A-Za-z]", "", number or "").upper()
        m = re.match(r"^[A-Z]{2}\d+([A-Z]\d?)$", t)
        return m.group(1) if m else ""

    def find_for_row(row):
        """Record for a known number. A kind code in the row (B1, A1 ...) wins; without a match on the
        kind, another kind code of the same number is used so the row still counts as seen."""
        want = _row_kind(row["number"])
        same_number = []
        for rid, raw in all_recs():
            if C.numbers_match(row["number"], _pub_number(raw)):
                if not want or (raw.get("kind") or "").upper() == want:
                    return rid
                same_number.append(rid)
            elif C.numbers_match(row["number"], raw.get("app_number", "")):
                same_number.append(rid)
        return same_number[0] if same_number else None

    if ops is not None and known_state:
        for ks in known_state:
            if find_for_row(ks["row"]):
                continue
            num = C.norm_number(ks["row"]["number"])
            if limits.get("max_lookup_calls", 200) <= diag["lookup_calls"]:
                break
            try:
                diag["lookup_calls"] += 1
                recs = ops.lookup(num, "publication")
                dd = _docdb_ref(ks["row"]["number"])
                if not recs and dd:           # epodoc form differs for some offices; try docdb CC.number.KIND
                    diag["lookup_calls"] += 1
                    recs = ops.lookup(dd, "publication", "docdb")
                if not recs:
                    diag["lookup_calls"] += 1
                    recs = ops.lookup(num, "application")
            except OPSBlocked as exc:
                diag["errors"].append(str(exc))
                break
            except OPSError as exc:
                diag["errors"].append(f"lookup {num}: {exc}")
                continue
            for r in recs:
                rid = add_raw(r, "ops-lookup")
                accepted.setdefault(rid, {"level": "known", "score": 1.0, "name": "", "applicant": "",
                                          "reason": "On the known list"})
    if bq is not None and known_state:
        missing_rows = [ks["row"]["number"] for ks in known_state if not find_for_row(ks["row"])]
        if missing_rows:
            try:
                recs = bq.lookup(missing_rows)
                diag["queries"].append({"query": f"BigQuery: direct lookup of {len(missing_rows)} known numbers",
                                        "hits": len(recs), "total": len(recs), "error": ""})
                for r in recs:
                    rid = add_raw(r, "bq-lookup")
                    accepted.setdefault(rid, {"level": "known", "score": 1.0, "name": "", "applicant": "",
                                              "reason": "On the known list"})
            except Exception as exc:  # noqa: BLE001 - BigQuery trouble must not stop the run
                msg = f"{type(exc).__name__}: {exc}"[:300]
                diag["queries"].append({"query": "BigQuery: direct lookup of known numbers", "hits": 0, "total": 0, "error": msg})
                diag["errors"].append("BigQuery: " + msg)
    for ks in known_state:
        ks["rid"] = find_for_row(ks["row"])
        if ks["rid"]:
            sources.setdefault(ks["rid"], set()).add("known-list")
            accepted.setdefault(ks["rid"], {"level": "known", "score": 1.0, "name": "", "applicant": "",
                                            "reason": "On the known list"})
            review.pop(ks["rid"], None)

    # ---- pass 3: family members ------------------------------------------
    def absorb_family(members, source, accepted_fams):
        for r in members:
            rid = record_id(r["country"], r["doc_number"], r["kind"])
            if rid in candidates:
                sources.setdefault(rid, set()).add(source)
                continue
            add_raw(r, source)
            m, excluded = _best_match(r, names, keywords, excludes, suggested)
            if m and m["level"] in ("match", "close"):
                accepted[rid] = dict(m, signal="family member")
            elif r.get("family_id") in accepted_fams and not excluded:
                accepted[rid] = {"level": "family", "score": 0.0, "name": "",
                                 "applicant": (r["applicants"] or [""])[0],
                                 "reason": "Same legal family as an accepted record; the applicant name differs."}
            elif m:
                review[rid] = dict(m, why="Family member with a weaker name match.")

    if limits.get("expand_families", True):
        fam_rep = {}
        for rid in list(accepted):
            fid = candidates[rid].get("family_id")
            if fid and fid not in fam_rep:
                fam_rep[fid] = candidates[rid]
        accepted_fams = set(fam_rep)
        if bq is not None and fam_rep:
            try:
                members = bq.family(list(fam_rep))
                diag["queries"].append({"query": f"BigQuery: members of {len(fam_rep)} families",
                                        "hits": len(members), "total": len(members), "error": ""})
                absorb_family(members, "bq-family", accepted_fams)
            except Exception as exc:  # noqa: BLE001
                msg = f"{type(exc).__name__}: {exc}"[:300]
                diag["queries"].append({"query": "BigQuery: family members", "hits": 0, "total": 0, "error": msg})
                diag["errors"].append("BigQuery: " + msg)
        if ops is not None:
            for fid, rep in fam_rep.items():
                if diag["family_calls"] >= limits.get("max_family_calls", 120):
                    break
                try:
                    diag["family_calls"] += 1
                    members = ops.family(_pub_number(rep))
                except OPSBlocked as exc:
                    diag["errors"].append(str(exc))
                    break
                except OPSError as exc:
                    diag["errors"].append(f"family {fid}: {exc}")
                    continue
                absorb_family(members, "ops-family", accepted_fams)

    # ---- legal events for the records most worth checking ---------------
    legal: dict[str, list] = {}
    if ops is not None and limits.get("max_legal_calls", 150) > 0:
        def prio(rid):
            t = C.record_type(candidates[rid]["country"], candidates[rid]["kind"])
            return (0 if t["stage"] == "grant" else 1, rid)
        for rid in sorted(accepted, key=prio):
            if diag["legal_calls"] >= limits.get("max_legal_calls", 150):
                break
            raw = candidates[rid]
            try:
                diag["legal_calls"] += 1
                legal[rid] = ops.legal(_pub_number(raw))
            except OPSBlocked as exc:
                diag["errors"].append(str(exc))
                break
            except OPSError as exc:
                diag["errors"].append(f"legal {rid}: {exc}")

    # ---- build output records --------------------------------------------
    records = []
    baseline_run = not known_rows and not previous.get("records")
    for rid, m in sorted(accepted.items()):
        raw = candidates[rid]
        t = C.record_type(raw["country"], raw["kind"], raw["doc_number"])
        st = C.derive_status(t["type"], t["stage"], raw.get("filing_date", ""), legal.get(rid), today)
        prios = raw.get("priority_dates") or []
        earliest = prios[0] if prios else raw.get("filing_date", "")
        rec = {
            "id": rid,
            "number": f"{raw['country']} {raw['doc_number']} {raw['kind']}".strip(),
            "country": raw["country"], "doc_number": raw["doc_number"], "kind": raw["kind"],
            "title": raw.get("title", ""),
            "jurisdiction": raw["country"],
            "filing_date": raw.get("filing_date", ""),
            "pub_date": raw.get("pub_date", ""),
            "priority_date": earliest,
            "family_id": raw.get("family_id", ""),
            "applicants": raw.get("applicants", []),
            "inventors": raw.get("inventors", []),
            "cpc": raw.get("cpc", [])[:6],
            "type": t["type"], "stage": t["stage"], "type_certain": t["certain"],
            "status": st["status"], "status_class": st["class"], "status_estimated": st["estimated"],
            "status_basis": st["basis"],
            "match": m,
            "sources": sorted(sources.get(rid, [])),
            "links": C.links(raw["country"], raw["doc_number"], raw["kind"]),
            "flags": {},
            "topic": "", "topic_note": "",
        }
        records.append(rec)

    # ---- compare with known list and previous run ------------------------
    rid_to_rec = {r["id"]: r for r in records}
    rows_seen = 0
    for ks in known_state:
        row, rid = ks["row"], ks["rid"]
        if rid and rid in rid_to_rec:
            rows_seen += 1
            rec = rid_to_rec[rid]
            rec["flags"]["known"] = True
            if row.get("family") and not rec["topic"]:
                rec["topic"], rec["topic_note"] = row["family"], "from known list"
            old, new = status_class(row.get("status", "")), rec["status_class"]
            if old in _ORDER and new in _ORDER and _ORDER[new] > _ORDER[old]:
                rec["flags"]["changed"] = {"from": row.get("status", ""), "to": rec["status"]}
    known_norm = {C.norm_number(ks["row"]["number"]) for ks in known_state if ks["row"].get("number")}
    known_norm.discard("")
    prev_ids = {r["id"] for r in previous.get("records", [])} if previous else set()
    prev_by_id = {r["id"]: r for r in previous.get("records", [])} if previous else {}
    for rec in records:
        was_prev = rec["id"] in prev_ids or any(
            C.numbers_match(rec["number"], p["number"]) for p in previous.get("records", []))
        if rec["flags"].get("known"):
            pass
        elif was_prev:
            rec["flags"]["seen_before"] = True
            p = prev_by_id.get(rec["id"])
            if p and p.get("status_class") in _ORDER and rec["status_class"] in _ORDER \
                    and _ORDER[rec["status_class"]] > _ORDER[p["status_class"]]:
                rec["flags"]["changed"] = {"from": p["status"], "to": rec["status"]}
        elif C.norm_number(rec["number"]) in known_norm:
            # same document number as a known row, only another kind code (A1/A4/B1/C0 ...)
            rec["flags"]["new_kind"] = True
        elif baseline_run:
            rec["flags"]["baseline"] = True
        else:
            rec["flags"]["new"] = True

    # ---- known rows that nothing returned: keep, show as "not seen" -------
    missing = []
    for ks in known_state:
        if ks["rid"]:
            continue
        row = ks["row"]
        missing.append(row["number"])
        fd = C.iso(row.get("filing_date", ""))
        cc = re.match(r"^([A-Za-z]{2})", re.sub(r"[^0-9A-Za-z]", "", row["number"]))
        country = (cc.group(1).upper() if cc else row.get("jurisdiction", "")[:2].upper())
        t = row.get("type", "").lower().replace(" ", "_") or "unverified"
        records.append({
            "id": "known:" + C.norm_number(row["number"]), "number": row["number"], "country": country,
            "doc_number": "", "kind": "", "title": row.get("title", ""),
            "jurisdiction": row.get("jurisdiction", "") or country, "filing_date": fd, "pub_date": "",
            "priority_date": C.iso(row.get("priority_date", "")), "family_id": "", "applicants": [],
            "inventors": [], "cpc": [], "type": t if t in {"patent", "design", "utility_model"} else "unverified",
            "stage": "unknown", "type_certain": False,
            "status": row.get("status", "") or "Unknown", "status_class": status_class(row.get("status", "")),
            "status_estimated": True, "status_basis": "From the known list. No source returned this record in this run.",
            "match": {"level": "known", "score": 1.0, "name": "", "applicant": "", "reason": "On the known list"},
            "sources": ["known-list"], "links": {}, "flags": {"known": True, "not_seen": True},
            "topic": row.get("family", ""), "topic_note": "from known list" if row.get("family") else "",
        })

    coverage = None
    if known_rows:
        coverage = {"known_total": len(known_rows), "found": rows_seen,
                    "missing": missing, "new_found": sum(1 for r in records if r["flags"].get("new"))}

    review_list = []
    for rid, m in review.items():
        raw = candidates[rid]
        review_list.append({
            "id": rid, "number": f"{raw['country']} {raw['doc_number']} {raw['kind']}".strip(),
            "title": raw.get("title", ""), "applicants": raw.get("applicants", []),
            "family_id": raw.get("family_id", ""), "filing_date": raw.get("filing_date", ""),
            "level": m["level"], "score": m["score"], "brand_name": m["name"], "applicant": m.get("applicant", ""),
            "why": m.get("why", m.get("reason", "")),
            "links": C.links(raw["country"], raw["doc_number"], raw["kind"]),
        })

    return {
        "slug": brand["slug"], "name": brand.get("label", brand["slug"]),
        "names": names, "baseline_run": baseline_run,
        "records": records, "review": sorted(review_list, key=lambda x: -x["score"]),
        "coverage": coverage,
        "diag": {
            "queries": diag["queries"],
            "dropped": diag["dropped"].most_common(15),
            "excluded": diag["excluded"].most_common(10),
            "family_calls": diag["family_calls"], "legal_calls": diag["legal_calls"],
            "lookup_calls": diag["lookup_calls"], "errors": diag["errors"][:10],
        },
    }


def window_note(now: datetime | None = None) -> str:
    """EPO asks robots to run 19:00-07:00 GMT or at weekends."""
    now = now or datetime.now(timezone.utc)
    if now.weekday() >= 5 or now.hour >= 19 or now.hour < 7:
        return ""
    return ("This run started inside the EPO's busy hours (07:00 to 19:00 GMT on weekdays). "
            "The EPO asks automatic tools to run in the evening or at weekends.")
