"""Close-name matching for applicant names.

Goal: "Cardo Systems, Inc." == "Cardo Systems Inc" == "CARDO SYSTEMS INC [US]",
and for Chinese companies: pinyin spacing, translation variants and Chinese
characters are handled through per-brand name sets (see config.json).

Levels returned by match_name():
  "match" - normalised core name identical (score 1.0)
  "close" - very similar (score >= CLOSE_THRESHOLD) or contained in a longer string
  "weak"  - only a distinctive keyword is shared (needs a person to approve)
  None    - no relation, or excluded
"""
from __future__ import annotations

import difflib
import re
import unicodedata

CLOSE_THRESHOLD = 0.90

# Legal-form words. Removed before comparing (they are a secondary signal).
LEGAL_TOKENS = {
    "inc", "incorporated", "ltd", "limited", "co", "company", "corp",
    "corporation", "llc", "gmbh", "ag", "sa", "bv", "pte", "plc", "lp", "llp",
    "kk", "oy", "ab", "srl", "spa", "pty", "pvt", "sdn", "bhd",
}
# Words with several spellings. Mapped to one form before comparing.
SYNONYMS = {
    "technologies": "tech", "technology": "tech", "technologie": "tech",
    "systems": "system", "international": "intl", "intl": "intl",
    "electronics": "electronic",
}
# Legal-form words in CJK scripts, removed from the end or the start.
CJK_LEGAL = (
    "股份有限公司", "有限责任公司", "有限責任公司", "有限公司", "株式会社",
    "株式會社", "주식회사", "(주)", "（株）", "㈱", "㈜",
)
# Taiwan adds "mainland company" in front of and "(Mainland China)" behind the name of a mainland company.
# They say nothing about who the applicant is, so they are removed before comparing.
CJK_NOISE = ("大陸商", "陸商", "大陆商", "陆商", "中國大陸", "中国大陆")
LOCATION_TOKENS = {"shenzhen", "hong", "kong", "hongkong", "guangdong", "shanghai", "beijing", "shi"}

_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"\[[^\]]*\]", " ", text)          # country tags like [US]
    for w in CJK_LEGAL + CJK_NOISE:
        text = text.replace(w, " ")
    text = text.replace("&", " and ")
    text = text.casefold()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)   # punctuation incl. commas
    text = text.replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def tokens(name: str) -> list[str]:
    """Normalised tokens: lower-case, no punctuation, legal forms removed, synonyms merged."""
    out = []
    for t in _clean(name).split():
        if t in LEGAL_TOKENS:
            continue
        out.append(SYNONYMS.get(t, t))
    return out


def core(name: str) -> str:
    """Core name as one string with spaces (spacing differences are ignored in compact())."""
    return " ".join(tokens(name))


def compact(name: str) -> str:
    return "".join(tokens(name))


def has_cjk(text: str) -> bool:
    return bool(_CJK.search(text or ""))


def search_phrase(name: str) -> str:
    """Phrase used in the EPO query: the name without punctuation and legal form."""
    t = _clean(name).split()
    t = [x for x in t if x not in LEGAL_TOKENS]
    return " ".join(t)


def _drop_location(toks: list[str]) -> list[str]:
    return [t for t in toks if t not in LOCATION_TOKENS]


def similarity(a: str, b: str) -> float:
    a, b = compact(a), compact(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _contains_seq(hay: list[str], needle: list[str]) -> bool:
    if not needle or len(needle) > len(hay):
        return False
    n = len(needle)
    return any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def is_excluded(candidate: str, excludes: list[str]) -> str | None:
    c = core(candidate)
    cc = compact(candidate)
    for ex in excludes or []:
        e = core(ex)
        if e and (e == c or _contains_seq(c.split(), e.split()) or compact(ex) in cc and len(compact(ex)) >= 6):
            return ex
    return None


def match_name(candidate: str, names: list[str], keywords: list[str] | None = None,
               excludes: list[str] | None = None) -> dict | None:
    """Compare one applicant string with every known name of a brand.

    Returns {"level","score","name","reason"} for the best match, or None.
    """
    ex = is_excluded(candidate, excludes or [])
    if ex:
        return None
    ctoks = tokens(candidate)
    if not ctoks:
        return None
    ccompact = "".join(ctoks)
    best = None

    def consider(level_rank, level, score, name, reason):
        nonlocal best
        if best is None or (level_rank, score) > (best[0], best[1]):
            best = (level_rank, score, {"level": level, "score": round(score, 3), "name": name, "reason": reason})

    for name in names:
        ntoks = tokens(name)
        if not ntoks:
            continue
        ncompact = "".join(ntoks)
        if ncompact == ccompact:
            consider(3, "match", 1.0, name, "same name after ignoring case, punctuation, spacing and legal form")
            continue
        if _drop_location(ntoks) and "".join(_drop_location(ntoks)) == "".join(_drop_location(ctoks)):
            consider(2, "close", 0.97, name, "same name except for a place word (for example Shenzhen)")
            continue
        if not has_cjk(name) and _contains_seq(ctoks, ntoks):
            level = "close"
            consider(2, level, 0.95, name, "name found inside a longer applicant string")
            continue
        if has_cjk(name) and name_cjk_in(name, candidate):
            consider(2, "close", 0.95, name, "Chinese/Korean/Japanese name found in applicant string")
            continue
        r = difflib.SequenceMatcher(None, ncompact, ccompact).ratio()
        if r >= CLOSE_THRESHOLD:
            consider(2, "close", r, name, f"similar spelling ({r:.2f})")
    if best:
        return best[2]

    for kw in keywords or []:
        k = "".join(tokens(kw)) or kw.casefold()
        if len(k) >= (2 if has_cjk(k) else 4) and (k in ctoks or k in ccompact):
            return {"level": "weak", "score": 0.5, "name": kw,
                    "reason": f"shares the distinctive word '{kw}' only"}
    return None


def name_cjk_in(name: str, candidate: str) -> bool:
    n = re.sub(r"\s+", "", unicodedata.normalize("NFKC", name))
    for w in CJK_LEGAL:
        n = n.replace(w, "")
    c = unicodedata.normalize("NFKC", candidate or "")
    for w in CJK_NOISE:
        c = c.replace(w, "")
    c = re.sub(r"\s+", "", c)
    return bool(n) and n in c
