"""Demo mode: runs the whole pipeline against invented records. Nothing here is a real patent."""
from __future__ import annotations

from .fakeops import FakeBQRunner, FakeHTTP, bq_row, exchange_doc as D

DEMO_BRAND = {
    "slug": "demo", "label": "Demo Helmet Co (invented)",
    "names": ["Demo Helmet Systems, Inc.", "Demo Helmet Systems Ltd."],
    "suggested_variants": ["Demo Helmet Tech Corporation"],
    "keywords": ["demohelmet"], "exclude": ["Demo Helmet Furniture"],
}
DEMO_KNOWN = [
    {"number": "US 9,000,111 B2", "title": "Helmet intercom pairing", "jurisdiction": "US", "status": "Pending",
     "family": "Helmet Bluetooth headset and intercom", "type": "patent"},
    {"number": "EP 3000222", "title": "Multitasking headset", "jurisdiction": "EP", "status": "Granted", "type": "patent"},
    {"number": "WO 2015/000333", "title": "Network audio relay", "jurisdiction": "WO", "status": "Granted", "type": "patent"},
]


def demo_http() -> FakeHTTP:
    a = ["Demo Helmet Systems, Inc."]
    docs = [
        D("US", "9000111", "B2", "111", "Helmet intercom pairing", a, ["Rivera, Ana"], "20160301", "20180605",
          [("US", "62000001", "20150301")], ["H04B1/385"]),
        D("US", "9555777", "B2", "777", "Group pairing of wireless headsets", ["DEMO HELMET SYSTEMS INC [US]"],
          ["Rivera, Ana", "Kim, Joon"], "20190410", "20210720", [("KR", "1020180001", "20180410")], ["H04W4/80"]),
        D("EP", "3777888", "A1", "888", "Helmet camera mount", ["Demo Helmet Systems Inc"], ["Kim, Joon"],
          "20200815", "20210224", [("US", "62100002", "20190815")], ["A42B3/04"]),
        D("US", "D0900123", "S1", "123", "Helmet speaker housing (ornamental design)", a, ["Lee, Sun"],
          "20190101", "20210105", [], []),
        D("CN", "210000001", "U", "001", "Helmet microphone boom", ["Demo Helmet Systems Ltd."], ["Wu, Tao"],
          "20190601", "20200114", [], ["H04R1/08"]),
        D("EP", "2100999", "B1", "999", "Portable audio repeater", a, ["Rivera, Ana"], "20050505", "20090812",
          [("US", "60000009", "20040505")], ["H04B7/155"]),
        D("EP", "2500444", "B1", "444", "Wireless headset roaming", a, ["Kim, Joon"], "20110202", "20140101",
          [("US", "61000004", "20100202")], ["H04W36/00"]),
        # similar name, but no inventor and no technology signal -> review
        D("US", "8123456", "B2", "456", "Garden furniture cover", ["Demo Helmets Systems Incorporated"], ["Smith, Bob"],
          "20180101", "20190101", [], ["A47C1/00"]),
        # only a suggested (unapproved) variant -> review
        D("US", "8333111", "B2", "311", "Visor coating", ["Demo Helmet Tech Corporation"], ["Chan, Mei"],
          "20180101", "20190301", [], []),
        # other company -> dropped
        D("US", "7000001", "B2", "001", "Unrelated thing", ["Demonstration Foods LLC"], [], "20150101", "20160101", [], []),
        # excluded
        D("US", "7000002", "B2", "002", "Chair", ["Demo Helmet Furniture Ltd"], [], "20150101", "20160101", [], []),
    ]
    family_member = D("JP", "2021999001", "A", "888", "Helmet camera mount", ["Demo Helmet KK"], [], "20210815",
                      "20220301", [("US", "62100002", "20190815")], [])
    return FakeHTTP(
        search={"demo helmet systems": docs},
        publications={"EP3000222": [D("EP", "3000222", "B1", "222", "Multitasking headset", a, ["Kim, Joon"],
                                      "20120101", "20150101", [], ["H04M1/60"])]},
        families={"EP3777888": [docs[2], family_member]},
        legal={"EP2500444": [("PG25", "LAPSED IN A CONTRACTING STATE: NON-PAYMENT OF ANNUAL FEE", "20190301")],
               "US9555777": [("MAINT", "MAINTENANCE FEE PAID", "20240101")]},
    )


def demo_bq_runner() -> FakeBQRunner:
    a = ["Demo Helmet Systems, Inc."]
    return FakeBQRunner([
        bq_row("US-9555777-B2", 777, "Group pairing of wireless headsets", a, ["Rivera, Ana", "Kim, Joon"], 20190410, 20180410, 20210720, ["H04W4/80"]),
        bq_row("EP-3777888-A1", 888, "Helmet camera mount", a, ["Kim, Joon"], 20200815, 20190815, 20210224, ["A42B3/04"]),
        bq_row("KR-20200055555-A", 555, "Helmet speaker pad", ["Demo Helmet Systems Inc"], ["Lee, Sun"], 20200901, 20200901, 20220301, ["H04R1/10"]),
        bq_row("WO-2015000333-A1", 333, "Network audio relay", a, ["Kim, Joon"], 20140501, 20130501, 20150108, ["H04L65/60"]),
        bq_row("US-7000001-B2", 1, "Unrelated thing", ["Demonstration Foods LLC"], [], 20150101, 20150101, 20160101, []),
    ])
