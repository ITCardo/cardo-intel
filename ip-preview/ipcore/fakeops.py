"""Offline stand-in for the EPO OPS server.

Used by --demo and by the tests. Builds XML in the layout described in the OPS 3.2 guide.
The records it serves are INVENTED. They are not real patents.
"""
from __future__ import annotations

import json
import re
from xml.sax.saxutils import escape as x

NS = 'xmlns:ops="http://ops.epo.org" xmlns="http://www.epo.org/exchange"'


def exchange_doc(country, number, kind, family, title, applicants, inventors=(), filing="20200101",
                 pub="20210101", priorities=(), cpc=(), app_number=None):
    app_number = app_number or number
    pri = "".join(
        f'<priority-claim sequence="{i + 1}" kind="national"><document-id document-id-type="docdb">'
        f'<country>{c}</country><doc-number>{n}</doc-number><kind>A</kind><date>{d}</date></document-id></priority-claim>'
        for i, (c, n, d) in enumerate(priorities))
    cp = ""
    for code in cpc:  # "H04B1/385"
        m = re.match(r"([A-H])(\d\d)([A-Z])(\d+)/(\d+)", code)
        if m:
            cp += (f'<patent-classification><section>{m.group(1)}</section><class>{m.group(2)}</class>'
                   f'<subclass>{m.group(3)}</subclass><main-group>{m.group(4)}</main-group>'
                   f'<subgroup>{m.group(5)}</subgroup></patent-classification>')
    ap = "".join(f'<applicant sequence="{i + 1}" data-format="original"><applicant-name><name>{x(a)}</name>'
                 f'</applicant-name></applicant>' for i, a in enumerate(applicants))
    inv = "".join(f'<inventor sequence="{i + 1}" data-format="original"><inventor-name><name>{x(a)}</name>'
                  f'</inventor-name></inventor>' for i, a in enumerate(inventors))
    return (
        f'<exchange-document system="ops.epo.org" family-id="{family}" country="{country}" '
        f'doc-number="{number}" kind="{kind}"><bibliographic-data>'
        f'<publication-reference><document-id document-id-type="docdb"><country>{country}</country>'
        f'<doc-number>{number}</doc-number><kind>{kind}</kind><date>{pub}</date></document-id></publication-reference>'
        f'<application-reference doc-id="{family}"><document-id document-id-type="docdb"><country>{country}</country>'
        f'<doc-number>{app_number}</doc-number><date>{filing}</date></document-id></application-reference>'
        f'<priority-claims>{pri}</priority-claims>'
        f'<patent-classifications>{cp}</patent-classifications>'
        f'<parties><applicants>{ap}</applicants><inventors>{inv}</inventors></parties>'
        f'<invention-title lang="en">{x(title)}</invention-title></bibliographic-data></exchange-document>')


def search_response(docs, total=None):
    total = len(docs) if total is None else total
    return (f'<?xml version="1.0"?><ops:world-patent-data {NS}><ops:biblio-search total-result-count="{total}">'
            f'<ops:query syntax="CQL">q</ops:query><ops:range begin="1" end="{len(docs)}"/>'
            f'<ops:search-result><exchange-documents>{"".join(f"<exchange-documents>{d}</exchange-documents>" for d in docs)}'
            f'</exchange-documents></ops:search-result></ops:biblio-search></ops:world-patent-data>').encode()


def docs_response(docs):
    return (f'<?xml version="1.0"?><ops:world-patent-data {NS}><exchange-documents>'
            f'{"".join(docs)}</exchange-documents></ops:world-patent-data>').encode()


def legal_response(events):
    ev = "".join(f'<ops:legal code="{x(c)}" desc="{x(d)}"><ops:L007EP>{dt}</ops:L007EP></ops:legal>' for c, d, dt in events)
    return (f'<?xml version="1.0"?><ops:world-patent-data {NS}><ops:patent-family><ops:family-member>'
            f'{ev}</ops:family-member></ops:patent-family></ops:world-patent-data>').encode()


class FakeHTTP:
    """Callable with the signature OPSClient expects: (method, url, headers, data, params)."""

    def __init__(self, search=None, publications=None, applications=None, families=None, legal=None):
        self.search = search or {}            # substring of CQL -> list of exchange-document xml strings
        self.publications = publications or {}  # epodoc number -> list of docs
        self.applications = applications or {}
        self.families = families or {}
        self.legal_events = legal or {}       # epodoc number -> list of (code, desc, date)
        self.log = []

    def __call__(self, method, url, headers=None, data=None, params=None):
        self.log.append((method, url, dict(params or {}), dict(headers or {})))
        if url.endswith("/auth/accesstoken"):
            return 200, {}, json.dumps({"access_token": "fake-token", "expires_in": "1199"}).encode()
        path = url.split("/rest-services", 1)[-1]
        if path.startswith("/published-data/search/biblio"):
            q = (params or {}).get("q", "").lower()
            for needle, docs in self.search.items():
                if needle.lower() in q:
                    return 200, {"x-throttling-control": "idle (search=green:30)"}, search_response(docs)
            return 404, {}, b'<fault><code>CLIENT.InvalidQuery</code><message>No results found</message></fault>'
        m = re.match(r"/published-data/(publication|application)/(?:epodoc|docdb)/([^/]+)/biblio", path)
        if m:
            table = self.publications if m.group(1) == "publication" else self.applications
            docs = table.get(m.group(2))
            return (200, {}, docs_response(docs)) if docs else (404, {}, b"<fault/>")
        m = re.match(r"/family/publication/epodoc/([^/]+)/biblio", path)
        if m:
            docs = self.families.get(m.group(1))
            return (200, {}, docs_response(docs)) if docs else (404, {}, b"<fault/>")
        m = re.match(r"/legal/publication/epodoc/([^/]+)$", path)
        if m:
            ev = self.legal_events.get(m.group(1))
            return (200, {}, legal_response(ev)) if ev else (404, {}, b"<fault/>")
        return 404, {}, b"<fault/>"


def bq_row(pn, family, title, assignee, inventor=(), filing=20200101, priority=20190101, pub=20210101, cpc=()):
    cc, num, kind = pn.split("-")
    return {"publication_number": pn, "application_number": "", "country_code": cc, "kind_code": kind,
            "family_id": str(family), "filing_date": filing, "priority_date": priority, "publication_date": pub,
            "title_en": title, "title_any": title, "assignee": list(assignee), "inventor": list(inventor),
            "cpc_codes": list(cpc)}


class FakeBQRunner:
    """Stand-in for ipcore.bq.BQRunner. Reads the '-- kind:' marker in the SQL. Rows are INVENTED."""

    def __init__(self, rows, fail_kinds=()):
        self.rows, self.fail_kinds = rows, set(fail_kinds)
        self.bytes_total, self.log = 0, []

    def run(self, sql, params):
        kind = re.match(r"-- kind: (\w+)", sql).group(1)
        self.log.append((kind, dict(params)))
        if kind in self.fail_kinds:
            raise RuntimeError("fake BigQuery failure")
        self.bytes_total += 10**9
        out = []
        for r in self.rows:
            if kind == "search":
                comp = [re.sub(r"[^\w]|_", "", a.lower()) for a in r["assignee"]]
                if any(p in c for p in params["pat"].split("|") for c in comp):
                    out.append(r)
            elif kind == "known":
                if r["publication_number"] in params["ids"] or any(r["publication_number"].startswith(p) for p in params["prefixes"]):
                    out.append(r)
            elif kind == "family":
                if r["family_id"] in params["fams"]:
                    out.append(r)
        return out
