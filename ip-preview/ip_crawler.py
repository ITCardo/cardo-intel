#!/usr/bin/env python3
"""IP crawler preview. Standalone: does not touch build.py, research/ or the main workflow.

  python ip-preview/ip_crawler.py                 # real run (needs EPO_OPS_KEY and EPO_OPS_SECRET)
  python ip-preview/ip_crawler.py --demo          # layout preview with invented records
  python ip-preview/ip_crawler.py --brands sena   # one brand only
Output: <out>/ip_preview.html and <out>/ip_results.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ipcore import crawler, demo, families as fam, render  # noqa: E402
from ipcore.epo import OPSClient  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--brands", default="", help="comma separated slugs; default all")
    ap.add_argument("--previous", default="", help="ip_results.json of an earlier run (to detect NEW and CHANGED)")
    ap.add_argument("--families", action="store_true", help="let Claude file NEW records under the families (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--demo", action="store_true", help="use invented records, no network")
    args = ap.parse_args(argv)

    cfg_path = Path(args.config)
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    sources, notes = [], []
    ops = None
    if args.demo:
        ops = OPSClient("demo", "demo", http=demo.demo_http(), min_interval=0, sleep=lambda s: None)
        cfg = dict(cfg, brands=[demo.DEMO_BRAND])
        sources.append({"name": "EPO Open Patent Services", "state": "read", "label": "demo",
                        "detail": "Invented records served from a fake server. No network call."})
    else:
        key, secret = os.environ.get("EPO_OPS_KEY", ""), os.environ.get("EPO_OPS_SECRET", "")
        if key and secret:
            ops = OPSClient(key, secret)
        else:
            notes.append("EPO_OPS_KEY and EPO_OPS_SECRET are not set, so no patent data was fetched. "
                         "Add both as repository secrets and run the workflow again.")
            sources.append({"name": "EPO Open Patent Services", "state": "off", "label": "no key",
                            "detail": "Credentials not configured."})
    sources.append({"name": "Google Patents", "state": "off", "label": "links only",
                    "detail": "Its search endpoint is closed to automated access (robots.txt). Each row links to the Google Patents page for manual checking."})
    sources.append({"name": "Espacenet", "state": "off", "label": "links only",
                    "detail": "Each row links to Espacenet. The data comes through the EPO service above."})
    wn = crawler.window_note()
    if wn and not args.demo:
        notes.append(wn)

    previous_all = {}
    if args.previous and Path(args.previous).exists():
        try:
            prev = json.loads(Path(args.previous).read_text(encoding="utf-8"))
            if prev.get("complete"):
                previous_all = {b["slug"]: b for b in prev.get("brands", [])}
                print(f"previous results loaded: {len(previous_all)} brand(s)")
            else:
                notes.append("The previous run was incomplete (no EPO key, an error, or demo data), so it was not used as the baseline.")
        except (ValueError, KeyError):
            notes.append("The previous results file could not be read, so this run is treated as a first run.")

    wanted = {s.strip() for s in args.brands.split(",") if s.strip()}
    brands_out = []
    for b in cfg["brands"]:
        if wanted and b["slug"] not in wanted:
            continue
        known = []
        if args.demo:
            known = demo.DEMO_KNOWN
        elif b.get("known_file"):
            known = crawler.load_known(cfg_path.parent / b["known_file"])
        print(f"== {b['slug']}: {len(known)} known records")
        try:
            res = crawler.run_brand(b, cfg, ops, known, previous_all.get(b["slug"]))
        except Exception as exc:  # noqa: BLE001 - one brand must not stop the others
            traceback.print_exc()
            res = {"slug": b["slug"], "name": b.get("label", b["slug"]), "names": b.get("names", []),
                   "baseline_run": False, "records": [], "review": [], "coverage": None,
                   "diag": {"queries": [], "dropped": [], "excluded": [], "family_calls": 0, "legal_calls": 0,
                            "lookup_calls": 0, "errors": [f"{type(exc).__name__}: {exc}"]}}
        if args.families and not args.demo:
            n = fam.assign_families(res["records"], cfg.get("families", []))
            print(f"   families assigned: {n}")
        s = res
        print(f"   records={len(s['records'])} new={sum(1 for r in s['records'] if r['flags'].get('new'))} "
              f"review={len(s['review'])} errors={len(s['diag']['errors'])}")
        brands_out.append(res)

    if ops is not None and not args.demo:
        quota = ", ".join(f"{k}: {v}" for k, v in ops.quota.items()) or "no quota header seen"
        blocked = ops.blocked
        sources[0] = {"name": "EPO Open Patent Services", "state": "off" if blocked else "read",
                      "label": "blocked" if blocked else "read",
                      "detail": (blocked or f"{ops.calls} calls. {quota}")}
    complete = bool(ops is not None and not args.demo and not ops.blocked
                    and brands_out and not any(b["diag"]["errors"] for b in brands_out))
    results = {"complete": complete, "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "demo": bool(args.demo),
               "notes": notes, "sources": sources, "brands": brands_out}
    (out / "ip_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "ip_preview.html").write_text(render.render(results), encoding="utf-8")
    print(f"written: {out / 'ip_preview.html'}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("## IP crawler preview\n\n")
            for n in notes:
                fh.write(f"- {n}\n")
            for b in brands_out:
                fh.write(f"- **{b['name']}**: {len(b['records'])} records, "
                         f"{sum(1 for r in b['records'] if r['flags'].get('new'))} new, {len(b['review'])} to review\n")
            fh.write("\nDownload `ip-preview` from the run's Artifacts and open `ip_preview.html`.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
