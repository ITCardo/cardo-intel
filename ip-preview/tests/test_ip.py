import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ipcore import classify as C  # noqa: E402
from ipcore import names as N  # noqa: E402
from ipcore import crawler, demo, render  # noqa: E402
from ipcore.epo import OPSBlocked, OPSClient, parse_exchange_documents, parse_legal_events  # noqa: E402
from ipcore.fakeops import FakeHTTP, exchange_doc as D, legal_response, search_response  # noqa: E402

CFG = json.loads((Path(__file__).resolve().parents[1] / "config.json").read_text(encoding="utf-8"))
BRANDS = {b["slug"]: b for b in CFG["brands"]}


# ------------------------------------------------------------- names
@pytest.mark.parametrize("cand", [
    "Cardo Systems, Inc.", "Cardo Systems Inc", "CARDO SYSTEMS INC [US]", "Cardo Systems Inc.,",
    "Cardo Systems Ltd", "Cardo Systems Limited",
])
def test_cardo_variants_match(cand):
    m = N.match_name(cand, BRANDS["cardo"]["names"], BRANDS["cardo"]["keywords"])
    assert m and m["level"] == "match"


def test_sena_tech_variants():
    names = BRANDS["sena"]["names"]
    for cand in ["SENA TECHNOLOGIES INC", "Sena Tech Inc.", "Sena Technologies, Inc", "SENA TECH"]:
        assert N.match_name(cand, names, ["sena"])["level"] == "match", cand
    assert N.match_name("세나테크놀로지", names)["level"] == "match"
    assert N.match_name("주식회사 세나테크놀로지", names)["level"] == "match"


def test_pinyin_spacing_and_location():
    names = BRANDS["reso"]["names"]
    assert N.match_name("Shenzhen Zi Wu Chuang Xin Technology Co Ltd", names)["level"] == "match"
    assert N.match_name("Ziwu Chuangxin Technology Co., Ltd.", names)["level"] == "close"
    assert N.match_name("Shenzhen Ziwu Chuangxin Tech", names)["level"] == "match"


def test_asmax_variants():
    names = BRANDS["asmax"]["names"]
    assert N.match_name("SHENZHEN ASMAX INFINITE TECHNOLOGY CO LTD", names)["level"] == "match"
    assert N.match_name("Hong Kong Yiheng International Technology Co., Limited", names)["level"] == "match"
    assert N.match_name("Yiheng International Technology Limited", names)["level"] == "close"
    weak = N.match_name("Asmax Corporation", names, ["asmax", "yiheng"])
    assert weak and weak["level"] == "weak"


def test_unrelated_and_excluded():
    names = BRANDS["cardo"]["names"]
    assert N.match_name("Cardiff Systems Inc", names, ["cardo"]) is None
    assert N.match_name("Sena Furniture Ltd", BRANDS["sena"]["names"], ["sena"], ["Sena Furniture"]) is None


def test_name_inside_longer_string():
    m = N.match_name("Cardo Systems Inc, a Delaware corporation", BRANDS["cardo"]["names"])
    assert m and m["level"] == "close"


def test_chinese_characters():
    names = ["深圳市赛纳科技有限公司"]
    assert N.match_name("深圳市赛纳科技有限公司", names)["level"] == "match"
    assert N.match_name("深圳市赛纳科技", names)["level"] == "match"
    w = N.match_name("赛纳电子", ["x"], ["赛纳"])
    assert w and w["level"] == "weak"


# ------------------------------------------------------------- classification
@pytest.mark.parametrize("c,k,n,typ,stage", [
    ("US", "B2", "10123456", "patent", "grant"), ("US", "A1", "2020123456", "patent", "application"),
    ("US", "S1", "D0900123", "design", "grant"), ("CN", "U", "210000001", "utility_model", "grant"),
    ("DE", "U1", "202020001", "utility_model", "grant"), ("CN", "S", "30000001", "design", "grant"),
    ("EP", "B1", "1000000", "patent", "grant"), ("WO", "A1", "2019123456", "patent", "application"),
    ("KR", "Y1", "200123456", "utility_model", "grant"), ("JP", "S", "1700001", "design", "grant"),
    ("US", "", "1", "unverified", "unknown"), ("US", "P2", "PP1", "unverified", "grant"),
])
def test_record_types(c, k, n, typ, stage):
    r = C.record_type(c, k, n)
    assert (r["type"], r["stage"]) == (typ, stage)


def test_status_term_and_events():
    today = date(2026, 10, 11)
    assert C.derive_status("patent", "grant", "2005-05-05", [], today)["class"] == "expired"
    assert C.derive_status("patent", "grant", "2015-05-05", [], today)["class"] == "granted"
    assert C.derive_status("utility_model", "grant", "2015-01-01", [], today)["class"] == "expired"
    assert C.derive_status("design", "grant", "1990-01-01", [], today)["class"] == "granted"   # not estimated
    ev = [{"code": "PG25", "desc": "LAPSED IN A CONTRACTING STATE", "date": "2019-03-01"}]
    s = C.derive_status("patent", "grant", "2020-01-01", ev, today)
    assert s["class"] == "expired" and not s["estimated"]
    ev2 = [{"code": "REIN", "desc": "REINSTATEMENT OF RIGHTS AFTER LAPSE", "date": "2019-03-01"}]
    assert C.derive_status("patent", "grant", "2020-01-01", ev2, today)["class"] == "granted"
    assert C.derive_status("patent", "application", "2020-01-01", [], today)["class"] == "pending"


def test_number_matching():
    assert C.numbers_match("US 10,123,456 B2", "US10123456")
    assert C.numbers_match("WO 2019/123456 A1", "WO2019123456")
    assert C.numbers_match("KR 10-2020-0012345", "KR20200012345")
    assert not C.numbers_match("US 10,123,456", "US10123457")
    assert not C.numbers_match("US 10123456", "EP10123456")


# ------------------------------------------------------------- parsing
def test_parse_exchange_document():
    xml = search_response([D("EP", "3777888", "A1", "888", "Helmet camera", ["Cardo Systems Inc [US]"],
                             ["Doe, Jane"], "20200815", "20210224", [("US", "62100002", "20190815")], ["A42B3/04"])])
    r = parse_exchange_documents(xml)[0]
    assert r["family_id"] == "888" and r["title"] == "Helmet camera"
    assert r["applicants"] == ["Cardo Systems Inc"] and r["inventors"] == ["Doe, Jane"]
    assert r["filing_date"] == "2020-08-15" and r["pub_date"] == "2021-02-24"
    assert r["priority_dates"] == ["2019-08-15"] and r["cpc"] == ["A42B 3/04"]


def test_parse_legal():
    ev = parse_legal_events(legal_response([("PG25", "LAPSED", "20190301")]))
    assert ev == [{"code": "PG25", "desc": "LAPSED", "date": "2019-03-01"}]


def test_empty_xml_documents():
    assert parse_exchange_documents(b"<ops:world-patent-data xmlns:ops='http://ops.epo.org'/>") == []


# ------------------------------------------------------------- client behaviour
def make_client(http):
    return OPSClient("k", "s", http=http, min_interval=0, sleep=lambda s: None)


def test_client_search_paging_and_header():
    docs = [D("US", str(1000 + i), "B2", str(i), "t", ["Cardo Systems Inc"]) for i in range(3)]
    http = FakeHTTP(search={"cardo": docs})
    c = make_client(http)
    recs, total = c.search('pa="cardo systems"', 300)
    assert len(recs) == 3 and total == 3
    search_calls = [x for x in http.log if "/search/" in x[1]]
    assert search_calls[0][3]["X-OPS-Range"] == "1-100"
    assert search_calls[0][3]["Authorization"] == "Bearer fake-token"
    auth = [x for x in http.log if x[1].endswith("/auth/accesstoken")][0]
    assert auth[3]["Authorization"].startswith("Basic ")


def test_client_no_results_is_empty_not_error():
    assert make_client(FakeHTTP()).search('pa="nothing"') == ([], 0)


def test_client_403_blocks_everything():
    def http(method, url, headers=None, data=None, params=None):
        if url.endswith("accesstoken"):
            return 200, {}, b'{"access_token":"t","expires_in":"1199"}'
        return 403, {"x-rejection-reason": "RegisteredQuotaPerWeek"}, b"<error/>"
    c = make_client(http)
    with pytest.raises(OPSBlocked):
        c.search('pa="x"')
    with pytest.raises(OPSBlocked):          # stays blocked, no further calls
        c.lookup("US1")
    assert "RegisteredQuotaPerWeek" in c.blocked


def test_client_bad_credentials():
    def http(method, url, headers=None, data=None, params=None):
        return 400, {}, b"{}"
    with pytest.raises(OPSBlocked):
        make_client(http).search('pa="x"')


def test_client_retries_503_then_succeeds():
    state = {"n": 0}

    def http(method, url, headers=None, data=None, params=None):
        if url.endswith("accesstoken"):
            return 200, {}, b'{"access_token":"t","expires_in":"1199"}'
        state["n"] += 1
        if state["n"] == 1:
            return 503, {}, b"busy"
        return 200, {}, search_response([D("US", "1", "B2", "1", "t", ["a"])])
    recs, _ = make_client(http).search('pa="x"')
    assert len(recs) == 1 and state["n"] == 2


# ------------------------------------------------------------- end to end
def run_demo(**kw):
    ops = make_client(demo.demo_http())
    cfg = dict(CFG)
    return crawler.run_brand(demo.DEMO_BRAND, cfg, ops, kw.get("known", demo.DEMO_KNOWN), kw.get("previous"),
                             today=date(2026, 10, 11), log=lambda *a: None)


def test_demo_pipeline():
    res = run_demo()
    by = {r["id"]: r for r in res["records"]}
    assert by["US9000111B2"]["flags"]["changed"]["to"] == "Granted"
    assert by["US9000111B2"]["flags"]["known"] and not by["US9000111B2"]["flags"].get("new")
    assert by["US9555777B2"]["flags"]["new"]
    assert by["EP2500444B1"]["status_class"] == "expired" and not by["EP2500444B1"]["status_estimated"]
    assert by["EP2100999B1"]["status_class"] == "expired" and by["EP2100999B1"]["status_estimated"]
    assert by["USD0900123S1"]["type"] == "design" and by["CN210000001U"]["type"] == "utility_model"
    assert by["JP2021999001A"]["match"]["level"] == "family"
    assert "known:WO2015000333" in by and by["known:WO2015000333"]["flags"]["not_seen"]
    assert res["coverage"] == {"known_total": 3, "found": 2, "missing": ["WO 2015/000333"], "new_found": 7}
    ids = {r["id"] for r in res["review"]}
    assert ids == {"US8333111B2", "US8123456B2"}              # suggested variant + close name without signal
    assert not any(r["id"] in ids for r in res["records"])
    dropped = dict(res["diag"]["dropped"])
    assert "Demonstration Foods LLC" in dropped
    assert res["diag"]["excluded"][0][0] == "Demo Helmet Furniture Ltd"


def test_first_run_without_known_list_is_baseline():
    res = run_demo(known=[])
    assert res["baseline_run"]
    assert not any(r["flags"].get("new") for r in res["records"])
    assert all(r["flags"].get("baseline") for r in res["records"])


def test_second_run_uses_previous():
    first = run_demo(known=[])
    second = run_demo(known=[], previous=first)
    assert not second["baseline_run"]
    assert not any(r["flags"].get("new") for r in second["records"])
    trimmed = dict(first, records=[r for r in first["records"] if r["id"] != "US9555777B2"])
    third = run_demo(known=[], previous=trimmed)
    assert [r["id"] for r in third["records"] if r["flags"].get("new")] == ["US9555777B2"]


def test_no_ops_means_no_records_and_known_not_seen():
    res = crawler.run_brand(demo.DEMO_BRAND, CFG, None, demo.DEMO_KNOWN, None, today=date(2026, 10, 11))
    assert len(res["records"]) == 3 and all(r["flags"]["not_seen"] for r in res["records"])


def test_blocked_mid_run_keeps_partial_results():
    http = demo.demo_http()
    calls = {"n": 0}

    def flaky(method, url, headers=None, data=None, params=None):
        if "/family/" in url:
            return 403, {"x-rejection-reason": "quota"}, b"x"
        return http(method, url, headers, data, params)
    res = crawler.run_brand(demo.DEMO_BRAND, CFG, make_client(flaky), demo.DEMO_KNOWN, None, today=date(2026, 10, 11))
    assert len(res["records"]) >= 8 and res["diag"]["errors"]


def test_known_csv_loader(tmp_path):
    f = tmp_path / "k.csv"
    f.write_text("# comment\nnumber,title,status\nUS 1 B2,A,Pending\n,empty,\n", encoding="utf-8")
    rows = crawler.load_known(f)
    assert len(rows) == 1 and rows[0]["number"] == "US 1 B2"
    assert crawler.load_known(tmp_path / "missing.csv") == []


def test_shipped_known_template_is_empty():
    assert crawler.load_known(Path(__file__).resolve().parents[1] / "known" / "sena.csv") == []


# ------------------------------------------------------------- rendering
def test_render_escapes_script_end_and_keeps_json_valid(tmp_path):
    results = {"generated": "x", "demo": True, "notes": ["</script><b>x</b>"], "sources": [],
               "brands": [run_demo()]}
    html = render.render(results)
    assert "</script><b>" not in html
    body = html.split("const DATA = ", 1)[1].split(";\nconst TYPE_LABEL", 1)[0]
    json.loads(body.replace("<\\/", "</"))


def test_empty_previous_still_counts_as_first_run():
    res = run_demo(known=[], previous={"records": []})
    assert res["baseline_run"] and not any(r["flags"].get("new") for r in res["records"])


def test_cli_demo_and_incomplete_previous(tmp_path):
    import ip_crawler
    out = tmp_path / "o"
    assert ip_crawler.main(["--demo", "--out", str(out)]) == 0
    data = json.loads((out / "ip_results.json").read_text(encoding="utf-8"))
    assert data["demo"] and data["complete"] is False
    assert "DEMO DATA" in (out / "ip_preview.html").read_text(encoding="utf-8")
    out2 = tmp_path / "o2"
    ip_crawler.main(["--out", str(out2), "--previous", str(out / "ip_results.json"), "--brands", "cardo"])
    d2 = json.loads((out2 / "ip_results.json").read_text(encoding="utf-8"))
    assert any("incomplete" in n for n in d2["notes"]) and any("not set" in n for n in d2["notes"])
