"""Google Patents Public Data in BigQuery (patents-public-data.patents.publications).

Official Google dataset, queried with SQL. No scraping. Used as a second source next to the EPO.
Verified columns (checked against the dataset's INFORMATION_SCHEMA): publication_number, country_code,
kind_code, family_id, application_number, filing_date / priority_date / publication_date (INT64 YYYYMMDD),
title_localized, assignee (ARRAY<STRING>), inventor (ARRAY<STRING>), cpc (ARRAY<STRUCT<code,...>>).

Number format note: US application publications are written with 10 digits (US-2015105022-A1),
not 11 (US 20150105022 A1). See classify.canon_docnum.
"""
from __future__ import annotations

import re

from . import names as N
from .classify import canon_docnum, iso

TABLE = "`patents-public-data.patents.publications`"

COLS = """publication_number, application_number, country_code, kind_code, family_id,
  filing_date, priority_date, publication_date,
  (SELECT t.text FROM UNNEST(title_localized) t WHERE t.language = 'en' LIMIT 1) AS title_en,
  (SELECT t.text FROM UNNEST(title_localized) t LIMIT 1) AS title_any,
  assignee, inventor,
  ARRAY(SELECT c.code FROM UNNEST(cpc) c LIMIT 8) AS cpc_codes"""

GENERIC_TAIL = {"tech", "system", "intl", "electronic"}


class BQError(Exception):
    pass


class BQTooBig(BQError):
    pass


def _compact_pattern(name: str) -> str:
    """Short compact string that identifies a company in a compacted applicant name.

    'Sena Technologies, Inc.' -> 'senatech'; 'Cardo Systems Ltd.' -> 'cardosystem';
    'Shenzhen Asmax Infinite Technology Co., Ltd.' -> 'asmaxinfinite'; 'Resosport Limited' -> 'resosport'.
    Spacing differences (pinyin) disappear because everything is compacted.
    """
    toks = [t for t in N.tokens(name) if t not in N.LOCATION_TOKENS]
    if not toks:
        return ""
    if N.has_cjk(name):
        return "".join(toks)
    out = toks[0]
    if len(out) < 8 and len(toks) > 1:
        out += toks[1]
    return re.sub(r"[^\w]", "", out, flags=re.UNICODE).lower()


def brand_patterns(brand: dict) -> list[str]:
    names = list(brand.get("names", [])) + list(brand.get("approved_aliases", [])) + list(brand.get("suggested_variants", []))
    pats = []
    for n in names:
        p = _compact_pattern(n)
        if len(p) >= 4 and p not in pats:
            pats.append(p)
    return pats


def compact_applicant(s: str) -> str:
    return re.sub(r"[^\w]|_", "", (s or "").lower(), flags=re.UNICODE)


def hits_patterns(raw: dict, pats: list[str]) -> bool:
    for a in raw.get("applicants", []):
        c = compact_applicant(a)
        if any(p in c for p in pats):
            return True
    return False


def bq_id(number: str) -> tuple[str, str]:
    """'US20150105022A1' -> ('US-2015105022-A1', 'US-2015105022-'); ('', prefix) when no kind code."""
    t = re.sub(r"[^0-9A-Za-z]", "", number or "").upper()
    m = re.match(r"^([A-Z]{2})(\d+)([A-Z]\d?)?$", t)
    if not m:
        return "", ""
    cc, digits, kind = m.group(1), canon_docnum(m.group(1), m.group(2)), m.group(3) or ""
    return (f"{cc}-{digits}-{kind}" if kind else ""), f"{cc}-{digits}-"


def row_to_raw(row: dict) -> dict:
    pn = row.get("publication_number", "")
    parts = pn.split("-")
    cc = row.get("country_code") or (parts[0] if parts else "")
    num = parts[1] if len(parts) > 2 else (parts[1] if len(parts) > 1 else "")
    kind = row.get("kind_code") or (parts[2] if len(parts) > 2 else "")
    prio = iso(row.get("priority_date")) if row.get("priority_date") else ""
    cpc = []
    for c in row.get("cpc_codes") or []:
        m = re.match(r"^([A-H]\d{2}[A-Z])\s*(\d+)\s*/\s*(\d+)", c or "")
        if m:
            cpc.append(f"{m.group(1)} {m.group(2)}/{m.group(3)}")
    fam = str(row.get("family_id") or "")
    return {
        "country": cc, "doc_number": num, "kind": kind,
        "family_id": "" if fam in ("-1", "None") else fam,
        "title": row.get("title_en") or row.get("title_any") or "",
        "applicants": [a for a in (row.get("assignee") or []) if a],
        "inventors": [i for i in (row.get("inventor") or []) if i],
        "filing_date": iso(row.get("filing_date")) if row.get("filing_date") else "",
        "pub_date": iso(row.get("publication_date")) if row.get("publication_date") else "",
        "priority_dates": [prio] if prio else [],
        "app_number": "",
        "cpc": cpc, "ipc": [],
    }


class BQRunner:
    """Thin wrapper around google-cloud-bigquery. Dry-runs every query first and refuses a query
    that would scan more than max_bytes (default 300 GB), so cost can never run away."""

    def __init__(self, project: str, max_bytes: int = 300 * 10**9, client=None):
        from google.cloud import bigquery
        self._bq = bigquery
        self.client = client or bigquery.Client(project=project)
        self.max_bytes = max_bytes
        self.bytes_total = 0
        self.cache_hits = 0
        self.queries = 0

    def run(self, sql: str, params: dict) -> list[dict]:
        bq = self._bq
        qp = []
        for k, v in params.items():
            if isinstance(v, list):
                qp.append(bq.ArrayQueryParameter(k, "STRING", v))
            elif isinstance(v, int):
                qp.append(bq.ScalarQueryParameter(k, "INT64", v))
            else:
                qp.append(bq.ScalarQueryParameter(k, "STRING", v))
        dry = self.client.query(sql, job_config=bq.QueryJobConfig(dry_run=True, use_query_cache=False, query_parameters=qp))
        if (dry.total_bytes_processed or 0) > self.max_bytes:
            raise BQTooBig(f"query would scan {dry.total_bytes_processed / 1e9:.0f} GB, above the limit of {self.max_bytes / 1e9:.0f} GB")
        cfg = bq.QueryJobConfig(query_parameters=qp, maximum_bytes_billed=self.max_bytes)
        job = self.client.query(sql, job_config=cfg)
        rows = [dict(r.items()) for r in job.result()]
        self.queries += 1
        self.bytes_total += job.total_bytes_billed or 0
        if getattr(job, "cache_hit", False):
            self.cache_hits += 1
        return rows


class BQSource:
    def __init__(self, runner, limit: int = 5000):
        self.runner = runner
        self.limit = limit
        self.cache: list[dict] | None = None
        self.error = ""
        self.queries = 0
        self.fam_cache: dict[str, list[dict]] = {}
        self.fam_done: set[str] = set()

    def _run(self, kind: str, body: str, params: dict) -> list[dict]:
        sql = f"-- kind: {kind}\nSELECT {COLS}\nFROM {TABLE} p\nWHERE {body}\nLIMIT @lim"
        self.queries += 1
        return self.runner.run(sql, dict(params, lim=self.limit))

    def prefetch(self, brands: list[dict]) -> None:
        """One search query for all brands. Matching to a brand happens later, in Python."""
        pats = sorted({p for b in brands for p in brand_patterns(b)})
        if not pats:
            self.cache = []
            return
        body = ("EXISTS (SELECT 1 FROM UNNEST(p.assignee) a WHERE "
                "REGEXP_CONTAINS(REGEXP_REPLACE(LOWER(a), r'[^\\p{L}\\p{N}]', ''), @pat))")
        try:
            rows = self._run("search", body, {"pat": "|".join(pats)})
            self.cache = [row_to_raw(r) for r in rows]
        except Exception as exc:  # noqa: BLE001
            self.error = f"{type(exc).__name__}: {exc}"[:300]
            self.cache = []
            return
        self._prefetch_families(brands)

    def _prefetch_families(self, brands: list[dict]) -> None:
        """One family query for every brand together (a BigQuery query is billed by the data it scans,
        so one query for all brands costs a quarter of one per brand). Families of candidate records
        that are only excluded names are left out. If this fails, family() asks again on demand."""
        fids = set()
        for b in brands:
            pats, excl = brand_patterns(b), b.get("exclude", [])
            for r in self.candidates_for(b):
                real = [a for a in r.get("applicants", [])
                        if any(p in compact_applicant(a) for p in pats) and not N.is_excluded(a, excl)]
                if real and r.get("family_id"):
                    fids.add(r["family_id"])
        if fids:
            try:
                self.family(sorted(fids))
            except Exception:  # noqa: BLE001 - the per-brand fallback will report the error
                pass

    def candidates_for(self, brand: dict) -> list[dict]:
        pats = brand_patterns(brand)
        return [r for r in (self.cache or []) if hits_patterns(r, pats)]

    def lookup(self, numbers: list[str]) -> list[dict]:
        ids, prefixes = [], []
        for n in numbers:
            i, p = bq_id(n)
            if i:
                ids.append(i)
            elif p:
                prefixes.append(p)
        if not ids and not prefixes:
            return []
        body = ("(p.publication_number IN UNNEST(@ids) OR EXISTS (SELECT 1 FROM UNNEST(@prefixes) pf "
                "WHERE STARTS_WITH(p.publication_number, pf)))")
        return [row_to_raw(r) for r in self._run("known", body, {"ids": ids, "prefixes": prefixes})]

    def family(self, family_ids: list[str]) -> list[dict]:
        fams = sorted({f for f in family_ids if f and f != "-1"})
        if not fams:
            return []
        need = [f for f in fams if f not in self.fam_done]
        if need:
            body = "p.family_id IN UNNEST(@fams)"
            for r in self._run("family", body, {"fams": need}):
                raw = row_to_raw(r)
                self.fam_cache.setdefault(raw["family_id"], []).append(raw)
            self.fam_done.update(need)
        return [r for f in fams for r in self.fam_cache.get(f, [])]

    def stats(self) -> str:
        b = getattr(self.runner, "bytes_total", 0)
        hits = getattr(self.runner, "cache_hits", 0)
        if b:
            tail = f", about {b / 1e9:.0f} GB billed"
        elif hits and hits >= self.queries:
            tail = ", all answered from Google's cache (the same query ran within 24 hours): nothing billed"
        else:
            tail = ""
        return f"{self.queries} queries" + tail
