import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ipcore import classify as C  # noqa: E402
from ipcore import names as N  # noqa: E402
from ipcore import bq as bqmod, crawler, demo, render  # noqa: E402
from ipcore.epo import OPSBlocked, OPSClient, parse_exchange_documents, parse_legal_events  # noqa: E402
from ipcore.fakeops import FakeBQRunner, FakeHTTP, bq_row, exchange_doc as D, legal_response, search_response  # noqa: E402

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


def test_shipped_sena_known_list():
    rows = crawler.load_known(Path(__file__).resolve().parents[1] / "known" / "sena.csv")
    assert len(rows) == 37
    assert len({C.norm_number(r["number"]) for r in rows}) == 36 or len(rows) == 37   # A1/A4/B1 of one EP share a base
    types = {r["number"]: r["type"] for r in rows}
    assert types["KR200433416Y1"] == "utility_model" and types["US8688040B2"] == "patent"
    assert all(r["jurisdiction"] == r["number"][:2] for r in rows)


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


def test_docdb_fallback_for_known_numbers():
    doc = D("US", "20150105022", "A1", "5", "Pairing", ["Sena Technologies, Inc."])
    http = FakeHTTP(publications={"US.20150105022.A1": [doc]})   # epodoc form misses, docdb form hits
    row = {"number": "US20150105022A1"}
    res = crawler.run_brand(BRANDS["sena"], CFG, make_client(http), [row], None, today=date(2026, 10, 11))
    assert res["coverage"]["found"] == 1 and res["records"][0]["id"] == "US2015105022A1"
    assert crawler._docdb_ref("KR 10-1076050 B1") == "KR.101076050.B1" and crawler._docdb_ref("EP3869839") == ""


# ------------------------------------------------------------- BigQuery source
def test_us_number_formats_are_one_document():
    assert C.norm_number("US 20150105022 A1") == C.norm_number("US2015105022A1") == "US2015105022"
    assert C.numbers_match("US20150105022A1", "US2015105022")
    assert C.numbers_match("US20150078724A1", "US2015078724")
    assert not C.numbers_match("US20150105022A1", "US2015105023")
    assert crawler.record_id("US", "20150105022", "A1") == crawler.record_id("US", "2015105022", "A1")
    assert C.norm_number("US 10,123,456 B2") == "US10123456"          # grants untouched


def test_bq_ids_and_patterns():
    assert bqmod.bq_id("US20150105022A1") == ("US-2015105022-A1", "US-2015105022-")
    assert bqmod.bq_id("KR200433416Y1") == ("KR-200433416-Y1", "KR-200433416-")
    assert bqmod.bq_id("EP3869839") == ("", "EP-3869839-")
    assert bqmod.brand_patterns(BRANDS["sena"]) == ["senatech", "세나테크놀로지", "セナテクノロジーズインコーポレイテッド"]
    cardo = bqmod.brand_patterns(BRANDS["cardo"])
    assert cardo[:2] == ["cardosystem", "cardointl"] and "卡多通讯系统" in cardo and "кардосистемс" in cardo
    assert set(bqmod.brand_patterns(BRANDS["reso"])) >= {"resosport", "ziwuchuangxin"}
    assert {"asmaxinfinite", "yihengintl"} <= set(bqmod.brand_patterns(BRANDS["asmax"]))


def test_bq_row_mapping():
    r = bqmod.row_to_raw(bq_row("US-2015105022-A1", 5, "Pairing", ["Sena Technologies Inc."], ["Kim, J"],
                                20141014, 20140901, 20150416, ["H04B1/385", "A42B3/04"]))
    assert (r["country"], r["doc_number"], r["kind"], r["family_id"]) == ("US", "2015105022", "A1", "5")
    assert r["filing_date"] == "2014-10-14" and r["priority_dates"] == ["2014-09-01"]
    assert r["cpc"] == ["H04B 1/385", "A42B 3/04"] and r["applicants"] == ["Sena Technologies Inc."]
    assert bqmod.row_to_raw(bq_row("KR-1-B1", -1, "t", []))["family_id"] == ""


SENA_ROWS = [
    bq_row("KR-101076050-B1", 45033260, "Helmet for bluetooth headset", ["주식회사 세나테크놀로지"], ["Kim"], 20100929, 20100929),
    bq_row("US-8688040-B2", 45033260, "Bluetooth headset for helmet", ["Sena Technologies Inc."], ["Kim"], 20101217, 20100929),
    bq_row("US-2015105022-A1", 7, "Pairing", ["Sena Technologies Inc."], ["Kim"], 20141014, 20141014),
    bq_row("US-9999999-B2", 99, "Garden chair", ["Sena Furniture Ltd"], [], 20100101, 20100101),
]


def run_sena(rows, known, fail_kinds=(), ops=None):
    src = bqmod.BQSource(FakeBQRunner(rows, fail_kinds))
    src.prefetch([BRANDS["sena"]])
    brand = dict(BRANDS["sena"], exclude=["Sena Furniture"])
    return crawler.run_brand(brand, CFG, ops, known, None, today=date(2026, 10, 11), bq=src), src


def test_bq_only_run_finds_and_matches_known_numbers():
    known = [{"number": "KR101076050B1"}, {"number": "US8688040B2"}, {"number": "US20150105022A1"}, {"number": "WO2020105895A1"}]
    res, src = run_sena(SENA_ROWS, known)
    ids = {r["id"] for r in res["records"]}
    assert {"KR101076050B1", "US8688040B2", "US2015105022A1"} <= ids
    assert "US9999999B2" not in ids                                   # other Sena, excluded
    assert res["coverage"]["found"] == 3 and res["coverage"]["missing"] == ["WO2020105895A1"]
    assert all("bq-search" in r["sources"] for r in res["records"] if not r["flags"].get("not_seen"))
    assert not any(r["flags"].get("new") for r in res["records"])


def test_bq_known_lookup_and_family_expansion():
    rows = [dict(r) for r in SENA_ROWS] + [bq_row("WO-2020105895-A1", 69669713, "Wireless intercom", ["Somebody Else GmbH"], [], 20191031, 20181120)]
    rows[0]["family_id"] = "69669713"
    known = [{"number": "WO2020105895A1"}]
    res, src = run_sena(rows, known)
    by = {r["id"]: r for r in res["records"]}
    assert "WO2020105895A1" in by and "bq-lookup" in by["WO2020105895A1"]["sources"]
    # family expansion: a member of an accepted family with a different applicant name is accepted as "family"
    rows2 = [r for r in SENA_ROWS[:1]] + [bq_row("EP-1-A1", 45033260, "Member", ["Other Co"], [], 20110101, 20100929)]
    res2, _ = run_sena(rows2, [])
    by2 = {r["id"]: r for r in res2["records"]}
    assert by2["EP1A1"]["match"]["level"] == "family" and "bq-family" in by2["EP1A1"]["sources"]


def test_bq_failure_does_not_stop_the_run():
    res, src = run_sena(SENA_ROWS, [], fail_kinds={"search"})
    assert src.error and res["diag"]["errors"] and res["records"] == []
    res2, _ = run_sena(SENA_ROWS, [{"number": "KR101076050B1"}], fail_kinds={"known", "family"})
    assert len(res2["records"]) >= 1 and any("BigQuery" in e for e in res2["diag"]["errors"])


def test_ops_and_bq_agree_on_one_record():
    docs = [D("US", "2015105022", "A1", "7", "Pairing", ["Sena Technologies Inc."], ["Kim"], "20141014", "20150416")]
    http = FakeHTTP(search={"sena": docs})
    res, _ = run_sena(SENA_ROWS, [], ops=make_client(http))
    rec = [r for r in res["records"] if r["id"] == "US2015105022A1"]
    assert len(rec) == 1 and {"ops-search", "bq-search"} <= set(rec[0]["sources"])


def test_bq_runner_refuses_expensive_query():
    class Job:
        total_bytes_processed = 900 * 10**9
        total_bytes_billed = 0

    class Client:
        def query(self, sql, job_config=None):
            return Job()

    class FakeLib:
        class QueryJobConfig:
            def __init__(self, **kw): pass
        class ArrayQueryParameter:
            def __init__(self, *a): pass
        class ScalarQueryParameter:
            def __init__(self, *a): pass

    r = bqmod.BQRunner.__new__(bqmod.BQRunner)
    r._bq, r.client, r.max_bytes, r.bytes_total, r.queries = FakeLib, Client(), 300 * 10**9, 0, 0
    with pytest.raises(bqmod.BQTooBig):
        r.run("SELECT 1", {"pat": "x"})


def test_cli_demo_has_two_sources(tmp_path):
    import ip_crawler
    ip_crawler.main(["--demo", "--out", str(tmp_path)])
    data = json.loads((tmp_path / "ip_results.json").read_text(encoding="utf-8"))
    assert any(s["name"].startswith("Google BigQuery") and s["state"] == "read" for s in data["sources"])
    both = [r for r in data["brands"][0]["records"] if {"ops-search", "bq-search"} <= set(r["sources"])]
    assert both


def test_sena_excludes_and_japanese_name():
    names, ex = BRANDS["sena"]["names"], BRANDS["sena"]["exclude"]
    for cand in ["Prosena Technologies B.V.", "Senatech Bilisim Teknoloji Sanayi Ticaret Anonim Sirketi"]:
        assert N.match_name(cand, names, ["sena"], ex) is None, cand
    assert N.match_name("Sena Technologies Inc.", names, ["sena"], ex)["level"] == "match"
    assert N.match_name("セナ  テクノロジーズ  インコーポレイテッド", names, ["sena"], ex)["level"] == "match"


def test_other_kind_code_of_known_number_is_not_new():
    rows = [bq_row("EP-3869839-A1", 69669713, "Pairing", ["Sena Technologies Inc."], [], 20191031, 20181120),
            bq_row("EP-3869839-B1", 69669713, "Pairing", ["Sena Technologies Inc."], [], 20191031, 20181120),
            bq_row("US-11889573-B2", 70472194, "Pairing", ["Sena Technologies Inc."], [], 20191031, 20190104)]
    res, _ = run_sena(rows, [{"number": "EP3869839B1"}])
    by = {r["id"]: r for r in res["records"]}
    assert by["EP3869839B1"]["flags"].get("known")
    assert by["EP3869839A1"]["flags"].get("new_kind") and not by["EP3869839A1"]["flags"].get("new")
    assert by["US11889573B2"]["flags"].get("new")
    assert res["coverage"]["new_found"] == 1


def test_asmax_has_no_generic_yiheng_pattern_and_chinese_names_match():
    pats = bqmod.brand_patterns(BRANDS["asmax"])
    assert "yiheng" not in pats and "asmaxinfinite" in pats
    assert BRANDS["asmax"]["keywords"] == ["asmax"]
    b = BRANDS["asmax"]
    assert N.match_name("深圳市纵贯无限科技有限公司", b["names"], b["keywords"], b["exclude"])["level"] == "match"
    assert N.match_name("大陸商深圳市縱貫無限科技有限公司 (中國大陸)", b["names"], b["keywords"], b["exclude"])["level"] in ("match", "close")
    r = BRANDS["reso"]
    assert N.match_name("深圳市子午创新技术有限公司", r["names"], r["keywords"], r["exclude"])["level"] == "match"
    c = BRANDS["cardo"]
    for cand in ["Cardo International GmbH", "卡多通讯系统有限公司", "カード・システムズ・インコーポレーテッド", "카르도 시스템즈, 인코퍼레이티드."]:
        assert N.match_name(cand, c["names"], c["keywords"], c["exclude"])["level"] in ("match", "close"), cand


def test_one_family_query_for_all_brands():
    rows = [dict(r) for r in SENA_ROWS]
    rows[0]["family_id"] = "45033260"
    rows.append(bq_row("EP-1-A1", 45033260, "Member", ["Other Co"], [], 20110101, 20100929))
    runner = FakeBQRunner(rows)
    src = bqmod.BQSource(runner)
    brands = [BRANDS["sena"], BRANDS["cardo"]]
    src.prefetch(brands)
    assert [k for k, _ in runner.log].count("family") == 1
    n = len(runner.log)
    members = src.family(["45033260"])                 # served from the cache: no new query
    assert len(runner.log) == n and any(m["doc_number"] == "1" for m in members)


def test_taiwan_mainland_company_wrapper_is_ignored():
    b = BRANDS["asmax"]
    for cand in ["大陸商深圳市縱貫無限科技有限公司 (中國大陸)", "大陸商深圳市縱貫無限科技有限公司", "大陆商深圳市纵贯无限科技有限公司（中国大陆）"]:
        assert N.match_name(cand, b["names"], b["keywords"], b["exclude"])["level"] == "match", cand
    assert "深圳市縱貫無限科技" in bqmod.compact_applicant("大陸商深圳市縱貫無限科技有限公司 (中國大陸)")


# ------------------------------------------------------------- product families
from ipcore import families as FAM  # noqa: E402
from ipcore.fakeops import FakeClaude  # noqa: E402


def _rec(i, fid, title, topic=""):
    return {"id": i, "number": i, "family_id": fid, "title": title, "cpc": [], "applicants": ["X"],
            "priority_date": "2020-01-01", "topic": topic, "topic_note": ""}


def _brand(*recs, slug="b"):
    return {"slug": slug, "name": slug, "records": list(recs)}


def test_config_has_nine_numbered_families():
    reg = FAM.build_registry(CFG["families"], None)
    assert [f["id"] for f in reg] == list(range(1, 10))
    assert reg[0]["name"] == "Wireless intercom - group pairing"
    assert reg[8]["name"] == "Legacy - network audio & FM transmission"


def test_family_order_override_known_previous_seed_claude():
    reg = FAM.build_registry(CFG["families"], None)
    recs = [_rec("a", "F1", "camera thing"), _rec("b", "F2", "camera thing", topic="5"),
            _rec("c", "F3", "camera thing"), _rec("d", "F4", "camera thing"), _rec("e", "F5", "camera thing")]
    b = _brand(*recs)
    out = FAM.assign([b], reg, {"b": {"F3": {"id": 7, "by": "claude", "note": "earlier"}}}, {"F1": 9},
                     seed={"F4": 6}, client=FakeClaude())
    got = {r["id"]: (r["topic_id"], r["topic_note"].split(":")[0]) for r in b["records"]}
    assert got["a"][0] == 9 and got["a"][1] == "Your grouping"          # override beats everything
    assert got["b"][0] == 5 and got["b"][1] == "Your grouping"          # known list
    assert got["c"][0] == 7                                              # previous run kept
    assert got["d"][0] == 6 and got["d"][1].startswith("Starting grouping")
    assert got["e"][0] == 4 and got["e"][1].startswith("Inferred by Claude")
    assert out["claude"] == 1 and out["created"] == []


def test_new_numbered_family_is_created_and_named_once():
    reg = FAM.build_registry(CFG["families"], None)
    b = _brand(_rec("a", "F1", "helmet visor"), _rec("b", "F2", "visor coating"))
    out = FAM.assign([b], reg, {}, {}, run_date="2026-10-11", client=FakeClaude())
    assert out["created"] == [10]
    assert reg[-1] == {"id": 10, "name": "Helmet visors and coatings", "created": "2026-10-11", "by": "claude"}
    assert [r["topic_id"] for r in b["records"]] == [10, 10]
    # next run: the registry from the results file brings it back, nothing new is created
    reg2 = FAM.build_registry(CFG["families"], reg)
    assert reg2[-1]["id"] == 10
    b2 = _brand(_rec("a", "F1", "helmet visor"), _rec("c", "F9", "visor shade"))
    out2 = FAM.assign([b2], reg2, {"b": b["family_map"]}, {}, client=FakeClaude())
    assert out2["created"] == [] and [r["topic_id"] for r in b2["records"]] == [10, 10]


def test_records_of_one_patent_family_share_one_decision():
    reg = FAM.build_registry(CFG["families"], None)
    client = FakeClaude()
    b = _brand(_rec("a", "F1", "camera mount"), _rec("b", "F1", "kamera halter"))
    FAM.assign([b], reg, {}, {}, client=client)
    assert [r["topic_id"] for r in b["records"]] == [4, 4]
    assert len(client.prompts) == 1 and client.prompts[0].count('"key": "F1"') == 1


def test_without_claude_unknown_records_stay_unfiled(capsys):
    reg = FAM.build_registry(CFG["families"], None)
    b = _brand(_rec("a", "F1", "camera mount"))
    out = FAM.assign([b], reg, {}, {}, use_claude=False)
    assert b["records"][0]["topic_id"] == 0 and out["claude"] == 0


def test_claude_failure_or_nonsense_never_breaks_the_run():
    class Broken:
        class messages:
            @staticmethod
            def create(**kw):
                raise RuntimeError("boom")
    reg = FAM.build_registry(CFG["families"], None)
    b = _brand(_rec("a", "F1", "camera mount"))
    FAM.assign([b], reg, {}, {}, client=Broken())
    assert b["records"][0]["topic_id"] == 0


def test_known_list_accepts_number_or_name():
    reg = FAM.build_registry(CFG["families"], None)
    assert FAM._find_family("3", reg) == 3 and FAM._find_family("F3", reg) == 3
    assert FAM._find_family("Portable Bluetooth repeater", reg) == 6
    assert FAM._find_family("nonsense", reg) is None


def test_every_seed_target_exists():
    ids = {f["id"] for f in CFG["families"]}
    assert set(CFG["family_seed"].values()) <= ids


def test_pending_wording():
    assert C.derive_status("patent", "application", "2024-01-01", [])["status"] == "Pending"


def test_demo_run_writes_families_and_reuses_them(tmp_path):
    import ip_crawler
    ip_crawler.main(["--demo", "--out", str(tmp_path)])
    d = json.loads((tmp_path / "ip_results.json").read_text(encoding="utf-8"))
    assert d["new_product_families"] == [10] and d["product_families"][-1]["id"] == 10
    assert all(r["topic_id"] for r in d["brands"][0]["records"])
    assert "demo" in d["family_maps"]
