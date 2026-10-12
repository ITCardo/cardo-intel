"""Rule-based record type, stage and status. No AI is used here."""
from __future__ import annotations

import re
from datetime import date, datetime

TERM_YEARS = {"patent": 20, "utility_model": 10}   # from filing date; designs are not estimated

LAPSE_WORDS = (
    "lapse", "lapsed", "withdrawn", "withdrawal", "refused", "refusal",
    "ceased", "cease", "revoked", "revocation", "expired", "expiry",
    "no longer in force", "deemed to be withdrawn", "abandon", "non-payment",
    "not paid", "terminated", "invalid", "annulled",
)
# Words that look like lapse words but mean the opposite or something else.
LAPSE_IGNORE = ("reinstat", "restor", "re-establish", "reestablish", "request for", "appeal against refusal")


def record_type(country: str, kind: str, number: str = "") -> dict:
    """Return {"type","stage","certain"}.

    type : patent | design | utility_model | unverified
    stage: application | grant | unknown
    """
    c = (country or "").upper()
    k = (kind or "").upper().strip()
    n = (number or "").upper()
    if not k:
        return {"type": "unverified", "stage": "unknown", "certain": False}
    letter = k[0]
    # designs
    if letter == "S" or (c == "US" and n.startswith("D")) or (c == "US" and k.startswith("S")):
        return {"type": "design", "stage": "grant", "certain": True}
    if letter == "F" and c in {"JP", "KR"}:       # JP/KR design variants
        return {"type": "design", "stage": "grant", "certain": False}
    # utility models
    if letter in {"U", "Y"} and c in {"CN", "DE", "KR", "JP", "ES", "TW", "RU", "UA", "BG", "CZ", "PL", "IT", "AT", "FI", "PT", "HU", "SK", "DK", "EE", "HR", "BR", "HK", "AU"} :
        return {"type": "utility_model", "stage": "grant", "certain": True}
    if letter in {"U", "Y"}:
        return {"type": "utility_model", "stage": "grant", "certain": False}
    # patents
    if letter == "A":
        return {"type": "patent", "stage": "application", "certain": True}
    if letter in {"B", "C", "E", "T"}:
        return {"type": "patent", "stage": "grant", "certain": True}
    if letter == "P":                               # US plant patents
        return {"type": "unverified", "stage": "grant", "certain": False}
    return {"type": "unverified", "stage": "unknown", "certain": False}


def parse_date(value) -> date | None:
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10] if "-" in s or "." in s or "/" in s else s[:8], fmt).date()
        except ValueError:
            continue
    return None


def iso(value) -> str:
    d = parse_date(value)
    return d.isoformat() if d else ""


# Events that mention a lapse/refusal word but do NOT end the whole right:
#  - lapses in some countries only (EP "lapsed in a contracting state", partial invalidation, "LT: ...")
#  - office actions that start a dialogue (JP/KR "notification of reasons for refusal")
PARTIAL_WORDS = ("in a contracting state", "contracting state", "partial", "partially",
                 "reason for refusal", "reasons for refusal", "intention to refuse",
                 "notice of reasons", "provisional refusal")
_COUNTRY_PREFIX = re.compile(r"^\s*[A-Z]{2}\s*:")


def _is_partial(ev: dict) -> bool:
    desc = str(ev.get("desc") or "")
    text = f"{desc} {ev.get('code', '')}".lower()
    return bool(_COUNTRY_PREFIX.match(desc)) or any(w in text for w in PARTIAL_WORDS)


def lapse_event(events: list[dict]) -> dict | None:
    """Latest legal event that signals the end of the whole right (lapse, withdrawal, refusal ...).
    National/partial lapses and office actions are skipped, see partial_events()."""
    hit = None
    for ev in events or []:
        text = f"{ev.get('desc', '')} {ev.get('code', '')}".lower()
        if any(w in text for w in LAPSE_IGNORE):
            continue
        if any(w in text for w in LAPSE_WORDS) and not _is_partial(ev):
            if hit is None or (ev.get("date") or "") > (hit.get("date") or ""):
                hit = ev
    return hit


def partial_events(events: list[dict]) -> list[dict]:
    """Lapse-like events that do not end the whole right (shown as a note only)."""
    out = []
    for ev in events or []:
        text = f"{ev.get('desc', '')} {ev.get('code', '')}".lower()
        if any(w in text for w in LAPSE_IGNORE):
            continue
        if any(w in text for w in LAPSE_WORDS) and _is_partial(ev):
            out.append(ev)
    return out


def partial_note(events: list[dict]) -> str:
    """Short text for the Status cell, empty when nothing to say."""
    parts = []
    for ev in sorted(partial_events(events), key=lambda e: e.get("date") or ""):
        desc = (ev.get("desc") or ev.get("code") or "").strip()
        low = desc.lower()
        if "reason" in low and "refusal" in low or "intention to refuse" in low or "provisional refusal" in low:
            label = "office action: refusal reasons notified"
        elif "contracting state" in low or _COUNTRY_PREFIX.match(desc) or "partial" in low:
            label = "lapsed / invalidated in some countries only"
        else:
            label = "partial event"
        item = label + (f" ({ev['date']})" if ev.get("date") else "")
        if item not in parts:
            parts.append(item)
    return "; ".join(parts[-2:])


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:                      # 29 Feb
        return d.replace(year=d.year + years, day=28)


def derive_status(rtype: str, stage: str, filing_date: str, events: list[dict] | None,
                  today: date | None = None) -> dict:
    """Status text, class (pending | granted | expired | unknown), how it was derived, and a note
    about partial events (lapse in some countries only, office actions)."""
    st = _derive(rtype, stage, filing_date, events, today)
    st["note"] = partial_note(events or [])
    return st


def _derive(rtype, stage, filing_date, events, today):
    today = today or date.today()
    ev = lapse_event(events or [])
    if ev:
        desc = ev.get("desc") or ev.get("code") or "legal event"
        return {"status": "Lapsed, withdrawn or refused", "class": "expired", "estimated": False,
                "basis": f"Legal event: {desc}" + (f" ({ev['date']})" if ev.get("date") else "")}
    fd = parse_date(filing_date)
    years = TERM_YEARS.get(rtype)
    if fd and years:
        end = add_years(fd, years)
        if end < today:
            return {"status": "Expired (term passed)", "class": "expired", "estimated": True,
                    "basis": f"Estimated: {years} years from filing date {fd.isoformat()} ended {end.isoformat()}"}
    if stage == "grant":
        return {"status": "Granted", "class": "granted", "estimated": True,
                "basis": "From the kind code. Legal status not confirmed by a legal event."}
    if stage == "application":
        return {"status": "Pending", "class": "pending", "estimated": True,
                "basis": "From the kind code. Not known whether it was later granted or dropped."}
    return {"status": "Unknown", "class": "unknown", "estimated": True, "basis": "Kind code not recognised."}


def canon_docnum(country: str, digits: str) -> str:
    """US application publications: 11 digits (2015 0105022) and 10 digits (2015105022) are the same
    document. Google and Espacenet use the 10-digit form. Returns the 10-digit form."""
    if country == "US" and re.fullmatch(r"(19|20)\d{2}0\d{6}", digits or ""):
        return digits[:4] + digits[5:]
    return digits


def norm_number(s: str) -> str:
    """Normalise a patent number string for comparison (no spaces, commas, slashes, dashes, kind code)."""
    t = re.sub(r"[^0-9A-Za-z]", "", s or "").upper()
    m = re.match(r"^([A-Z]{2})(.*)$", t)
    cc, rest = (m.group(1), m.group(2)) if m else ("", t)
    rest = re.sub(r"(?<=\d)[A-Z]\d?$", "", rest)     # trailing kind code, e.g. B2, A1, U
    return cc + canon_docnum(cc, rest)


def numbers_match(a: str, b: str) -> bool:
    """True when two numbers denote the same document (tolerates year prefixes such as KR 10-2020-0012345)."""
    na, nb = norm_number(a), norm_number(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if na[:2] != nb[:2]:
        return False
    da, db = na[2:], nb[2:]
    if min(len(da), len(db)) >= 8 and (da.endswith(db) or db.endswith(da)):
        return True
    return da.lstrip("0") == db.lstrip("0") and bool(da.lstrip("0"))


def links(country: str, doc_number: str, kind: str) -> dict:
    pub = f"{country}{doc_number}{kind}"
    return {
        "google": f"https://patents.google.com/patent/{pub}/en",
        "espacenet": f"https://worldwide.espacenet.com/patent/search?q=pn%3D{country}{doc_number}{kind}",
    }
