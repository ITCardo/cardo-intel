"""EPO Open Patent Services (OPS 3.2) client.

Follows the OPS 3.2 documentation (version 1.3.19):
  * token : POST /3.2/auth/accesstoken, Basic base64(key:secret), grant_type=client_credentials
  * search: GET  /3.2/rest-services/published-data/search/biblio?q=<CQL>   header X-OPS-Range: 1-100
            (max 100 per request, max 2000 results per query)
  * lookup: GET  /published-data/{publication|application}/epodoc/{number}/biblio
  * family: GET  /family/publication/epodoc/{number}/biblio
  * legal : GET  /legal/publication/epodoc/{number}
Responses are XML. Namespaces are ignored on purpose (matching on local names).

Never logs the key, the secret or the token.
"""
from __future__ import annotations

import base64
import json
import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote

from .classify import iso

BASE = "https://ops.epo.org/3.2"
REST = BASE + "/rest-services"


class OPSError(Exception):
    pass


class OPSNotFound(OPSError):
    pass


class OPSBlocked(OPSError):
    """Quota used up, fair-use block or robot detection. The run must stop calling OPS."""


def _default_http(method, url, headers=None, data=None, params=None):
    import requests
    r = requests.request(method, url, headers=headers, data=data, params=params, timeout=60)
    return r.status_code, {k.lower(): v for k, v in r.headers.items()}, r.content


def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _children(el, name):
    return [c for c in el if _local(c.tag) == name]


def _child(el, name):
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _text(el, name="") -> str:
    node = _child(el, name) if name else el
    return (node.text or "").strip() if node is not None else ""


def _find_all(el, name):
    return [c for c in el.iter() if _local(c.tag) == name]


def _docid(parent, kind_pref=("docdb", "epodoc")):
    """Return {"country","number","kind","date","type"} of the preferred document-id under parent."""
    ids = _children(parent, "document-id")
    by_type = {d.get("document-id-type"): d for d in ids}
    for t in kind_pref:
        d = by_type.get(t)
        if d is not None:
            return {"country": _text(d, "country"), "number": _text(d, "doc-number"),
                    "kind": _text(d, "kind"), "date": _text(d, "date"), "type": t}
    return {"country": "", "number": "", "kind": "", "date": "", "type": ""}


def _date_of(parent) -> str:
    """Date from any document-id under parent (docdb first, then epodoc, then anything)."""
    for t in ("docdb", "epodoc", None):
        for d in _children(parent, "document-id"):
            if t is None or d.get("document-id-type") == t:
                dt = _text(d, "date")
                if dt:
                    return dt
    return ""


def parse_exchange_documents(xml_bytes: bytes) -> list[dict]:
    """Parse every exchange-document in an OPS response into a plain dict."""
    root = ET.fromstring(xml_bytes)
    out = []
    seen = set()
    for doc in _find_all(root, "exchange-document"):
        country, number, kind = doc.get("country", ""), doc.get("doc-number", ""), doc.get("kind", "")
        if not (country and number):
            continue
        key = (country, number, kind)
        if key in seen:
            continue
        seen.add(key)
        biblio = _child(doc, "bibliographic-data")
        if biblio is None:
            out.append({"country": country, "doc_number": number, "kind": kind,
                        "family_id": doc.get("family-id", ""), "title": "", "applicants": [], "inventors": [],
                        "filing_date": "", "pub_date": "", "priority_dates": [], "cpc": [], "ipc": [],
                        "app_number": ""})
            continue
        pub = _child(biblio, "publication-reference")
        pub_id = _docid(pub) if pub is not None else {}
        app = _child(biblio, "application-reference")
        app_id = _docid(app) if app is not None else {}
        filing = _date_of(app) if app is not None else ""

        titles = _children(biblio, "invention-title")
        title = ""
        for t in titles:
            if t.get("lang") == "en" and (t.text or "").strip():
                title = t.text.strip()
                break
        if not title and titles:
            title = (titles[0].text or "").strip()

        def party_names(container_name, item_name, name_tag):
            res_original, res_other = [], []
            cont = None
            parties = _child(biblio, "parties")
            if parties is not None:
                cont = _child(parties, container_name)
            if cont is None:
                return []
            for item in _children(cont, item_name):
                nm = _child(item, name_tag)
                val = _text(nm, "name") if nm is not None else ""
                val = re.sub(r"\s*\[[A-Z]{2}\]\s*$", "", val).strip().rstrip(",").strip()
                if not val:
                    continue
                (res_original if item.get("data-format") == "original" else res_other).append(val)
            names = res_original + [n for n in res_other if n.casefold() not in {x.casefold() for x in res_original}]
            seen_n, uniq = set(), []
            for n in names:
                k = n.casefold()
                if k not in seen_n:
                    seen_n.add(k)
                    uniq.append(n)
            return uniq

        applicants = party_names("applicants", "applicant", "applicant-name")
        inventors = party_names("inventors", "inventor", "inventor-name")

        prios = []
        pcs = _child(biblio, "priority-claims")
        if pcs is not None:
            for pc in _children(pcs, "priority-claim"):
                d = _date_of(pc)
                if d:
                    prios.append(iso(d))
        prios = sorted({p for p in prios if p})

        cpc = set()
        for pcl in _find_all(biblio, "patent-classification"):
            sec, cls, sub = _text(pcl, "section"), _text(pcl, "class"), _text(pcl, "subclass")
            mg, sg = _text(pcl, "main-group"), _text(pcl, "subgroup")
            if sec and cls and sub:
                cpc.add(f"{sec}{cls}{sub}" + (f" {mg}/{sg}" if mg and sg else ""))
        ipc = set()
        for ic in _find_all(biblio, "classification-ipcr"):
            raw = re.sub(r"\s+", " ", _text(ic, "text") or (ic.text or "")).strip()
            m = re.match(r"^([A-H]\d{2}[A-Z])\s*(\d+)\s*/\s*(\d+)", raw)
            if m:
                ipc.add(f"{m.group(1)} {m.group(2)}/{m.group(3)}")

        out.append({
            "country": country,
            "doc_number": number,
            "kind": kind,
            "family_id": doc.get("family-id", ""),
            "title": title,
            "applicants": applicants,
            "inventors": inventors,
            "filing_date": iso(filing),
            "pub_date": iso(pub_id.get("date", "")) if pub_id else "",
            "priority_dates": prios,
            "app_number": (app_id.get("country", "") + app_id.get("number", "")) if app_id else "",
            "cpc": sorted(cpc),
            "ipc": sorted(ipc),
        })
    return out


def parse_search_meta(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes)
    meta = {"total": 0}
    for el in _find_all(root, "biblio-search"):
        try:
            meta["total"] = int(el.get("total-result-count", "0"))
        except ValueError:
            pass
    return meta


def parse_legal_events(xml_bytes: bytes) -> list[dict]:
    """Tolerant parser: any element with a 'code' and a 'desc' attribute is a legal event.

    The exact legal-service layout was not available in the OPS guide text used to write this,
    so the parser does not depend on element names. If a date child exists it is used.
    """
    root = ET.fromstring(xml_bytes)
    events = []
    for el in root.iter():
        code, desc = el.get("code"), el.get("desc")
        if code and desc:
            date = ""
            for ch in el.iter():
                v = (ch.text or "").strip()
                if re.fullmatch(r"\d{8}", v):
                    date = iso(v)
                    break
            events.append({"code": code, "desc": desc, "date": date})
    return events


class OPSClient:
    def __init__(self, key: str, secret: str, http=None, min_interval: float = 1.2, sleep=time.sleep,
                 now=time.time):
        self._key, self._secret = key, secret
        self._http = http or _default_http
        self._min_interval = min_interval
        self._sleep = sleep
        self._now = now
        self._token = ""
        self._token_until = 0.0
        self._last = 0.0
        self.calls = 0
        self.quota = {}
        self.blocked: str | None = None

    # -- auth ---------------------------------------------------------
    def _auth(self):
        cred = base64.b64encode(f"{self._key}:{self._secret}".encode()).decode()
        status, headers, body = self._http(
            "POST", BASE + "/auth/accesstoken",
            headers={"Authorization": f"Basic {cred}", "Content-Type": "application/x-www-form-urlencoded"},
            data="grant_type=client_credentials")
        if status != 200:
            raise OPSBlocked(f"OPS login failed (HTTP {status}). Check EPO_OPS_KEY and EPO_OPS_SECRET.")
        try:
            data = json.loads(body)
            self._token = data["access_token"]
            self._token_until = self._now() + max(60, int(float(data.get("expires_in", 1000))) - 60)
        except (ValueError, KeyError) as exc:
            raise OPSBlocked("OPS login returned an unexpected answer.") from exc

    # -- request ------------------------------------------------------
    def _request(self, path: str, params=None, extra_headers=None) -> bytes:
        if self.blocked:
            raise OPSBlocked(self.blocked)
        if not self._token or self._now() >= self._token_until:
            self._auth()
        attempt = 0
        refreshed = False
        while True:
            wait = self._min_interval - (self._now() - self._last)
            if wait > 0:
                self._sleep(wait)
            headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/xml"}
            headers.update(extra_headers or {})
            status, rh, body = self._http("GET", REST + path, headers=headers, params=params)
            self._last = self._now()
            self.calls += 1
            for h in ("x-registeredquotaperweek-used", "x-individualquotaperhour-used"):
                if h in rh:
                    self.quota[h] = rh[h]
            tc = rh.get("x-throttling-control", "")
            if status == 200:
                if re.search(r"=red", tc):
                    self._sleep(5)
                return body
            text = body[:400].decode("utf-8", "replace") if body else ""
            if status == 404:
                raise OPSNotFound(path)
            low = text.lower()
            if status in (400, 401) and not refreshed and ("token" in low or "invalid" in low or status == 401):
                refreshed = True
                self._auth()
                continue
            if status == 403:
                retry = rh.get("retry-after")
                if retry and attempt < 2:
                    try:
                        delay = min(float(retry) / 1000.0, 120.0)
                    except ValueError:
                        delay = 30.0
                    attempt += 1
                    self._sleep(delay)
                    continue
                reason = rh.get("x-rejection-reason", "") or re.sub(r"\s+", " ", text)[:160]
                self.blocked = f"OPS refused the request (HTTP 403): {reason}"
                raise OPSBlocked(self.blocked)
            if status in (408, 500, 502, 503, 504) and attempt < 3:
                attempt += 1
                self._sleep(2 ** attempt * 2)
                continue
            raise OPSError(f"OPS HTTP {status} for {path}: {re.sub(chr(10), ' ', text)[:160]}")

    # -- services -----------------------------------------------------
    def search(self, cql: str, max_results: int = 300) -> tuple[list[dict], int]:
        """Return (records, total_hits). Pages of 100, never more than 2000 results."""
        max_results = min(max_results, 2000)
        records, begin, total = [], 1, None
        while begin <= max_results:
            end = min(begin + 99, max_results)
            try:
                body = self._request("/published-data/search/biblio", params={"q": cql},
                                     extra_headers={"X-OPS-Range": f"{begin}-{end}"})
            except OPSNotFound:
                break
            if total is None:
                total = parse_search_meta(body)["total"]
            page = parse_exchange_documents(body)
            records.extend(page)
            if not page or begin + 99 >= (total or 0):
                break
            begin += 100
        return records, total or 0

    def lookup(self, number: str, ref_type: str = "publication") -> list[dict]:
        try:
            body = self._request(f"/published-data/{ref_type}/epodoc/{quote(number, safe='')}/biblio")
        except OPSNotFound:
            return []
        return parse_exchange_documents(body)

    def family(self, number: str) -> list[dict]:
        try:
            body = self._request(f"/family/publication/epodoc/{quote(number, safe='')}/biblio")
        except OPSNotFound:
            return []
        return parse_exchange_documents(body)

    def legal(self, number: str) -> list[dict]:
        try:
            body = self._request(f"/legal/publication/epodoc/{quote(number, safe='')}")
        except OPSNotFound:
            return []
        return parse_legal_events(body)
