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

from ipcore import bq as bqmod, crawler, demo, families as fam, render  # noqa: E402
from ipcore.epo import OPSClient  # noqa: E402
from ipcore.fakeops import FakeClaude  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--brands", default="", help="comma separated slugs; default all")
    ap.add_argument("--previous", default="", help="ip_results.json of an earlier run (to detect NEW and CHANGED)")
    ap.add_argument("--families", action="store_true", help="let Claude file records that are not yet in a product family (needs ANTHROPIC_API_KEY). Without it, only your own grouping and earlier decisions are applied")
    ap.add_argument("--demo", action="store_true", help="use invented records, no network")
    ap.add_argument("--no-bigquery", action="store_true", help="skip BigQuery even if configured")
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
    bq = None
    if args.demo:
        bq = bqmod.BQSource(demo.demo_bq_runner())
        sources.append({"name": "Google BigQuery patents", "state": "read", "label": "demo",
                        "detail": "Invented rows served from a fake runner. No network call."})
    elif os.environ.get("GCP_PROJECT") and not args.no_bigquery:
        try:
            runner = bqmod.BQRunner(os.environ["GCP_PROJECT"], int(float(os.environ.get("BQ_MAX_GB", "300")) * 10**9))
            bq = bqmod.BQSource(runner)
            sources.append({"name": "Google BigQuery patents", "state": "read", "label": "read", "detail": ""})
        except Exception as exc:  # noqa: BLE001 - missing library or credentials
            notes.append(f"BigQuery is configured but could not start ({type(exc).__name__}: {str(exc)[:160]}). This run uses the other sources only.")
            sources.append({"name": "Google BigQuery patents", "state": "off", "label": "not started", "detail": "See the note above."})
    else:
        sources.append({"name": "Google BigQuery patents", "state": "off", "label": "not configured",
                        "detail": "Set the GCP_SA_KEY secret and the GCP_PROJECT variable to turn it on."})
    sources.append({"name": "Google Patents", "state": "off", "label": "links only",
                    "detail": "The website's search endpoint is closed to automated access (robots.txt), so it is not scraped. Each row links to its Google Patents page. The official Google data comes through BigQuery."})
    sources.append({"name": "Espacenet", "state": "off", "label": "links only",
                    "detail": "Each row links to Espacenet. The data comes through the EPO service above."})
    wn = crawler.window_note()
    if wn and not args.demo:
        notes.append(wn)

    previous_all = {}
    prev_registry, prev_maps = [], {}
    if args.previous and Path(args.previous).exists():
        try:
            prev = json.loads(Path(args.previous).read_text(encoding="utf-8"))
            prev_registry = prev.get("product_families", []) or []       # kept even when the run was incomplete
            prev_maps = dict(prev.get("family_maps") or {})
            for pb in prev.get("brands", []):
                if pb.get("family_map") and pb["slug"] not in prev_maps:
                    prev_maps[pb["slug"]] = pb["family_map"]
            if prev.get("complete"):
                previous_all = {b["slug"]: b for b in prev.get("brands", [])}
                print(f"previous results loaded: {len(previous_all)} brand(s)")
            else:
                notes.append("The previous run was incomplete (no EPO key, an error, or demo data), so it was not used as the baseline.")
        except (ValueError, KeyError):
            notes.append("The previous results file could not be read, so this run is treated as a first run.")

    if bq is not None:
        active = [b for b in cfg["brands"] if not {x.strip() for x in args.brands.split(",") if x.strip()} or b["slug"] in {x.strip() for x in args.brands.split(",")}]
        bq.prefetch(active)
        print(f"BigQuery search: {len(bq.cache or [])} rows" + (f" ERROR {bq.error}" if bq.error else ""))
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
            res = crawler.run_brand(b, cfg, ops, known, previous_all.get(b["slug"]), bq=bq)
        except Exception as exc:  # noqa: BLE001 - one brand must not stop the others
            traceback.print_exc()
            res = {"slug": b["slug"], "name": b.get("label", b["slug"]), "names": b.get("names", []),
                   "baseline_run": False, "records": [], "review": [], "coverage": None,
                   "diag": {"queries": [], "dropped": [], "excluded": [], "family_calls": 0, "legal_calls": 0,
                            "lookup_calls": 0, "errors": [f"{type(exc).__name__}: {exc}"]}}
        s = res
        print(f"   records={len(s['records'])} new={sum(1 for r in s['records'] if r['flags'].get('new'))} "
              f"review={len(s['review'])} errors={len(s['diag']['errors'])}")
        brands_out.append(res)

    registry = fam.build_registry(cfg.get("families", []), prev_registry)
    fres = fam.assign(brands_out, registry, prev_maps, cfg.get("family_overrides", {}), seed=cfg.get("family_seed", {}),
                      client=FakeClaude() if args.demo else None, use_claude=bool(args.families or args.demo))
    print(f"product families: {len(registry)} defined, {fres['claude']} patent families filed by Claude, "
          f"{len(fres['created'])} new")
    if fres["created"]:
        notes.append("New product families created by Claude this run: " +
                     "; ".join(f"{f['id']} {f['name']}" for f in registry if f["id"] in fres["created"]) +
                     ". Check the names. To keep one, add it to \"families\" in config.json; to change a record, use \"family_overrides\".")
    family_maps = dict(prev_maps)
    family_maps.update({b["slug"]: b.get("family_map", {}) for b in brands_out})

    if ops is not None and not args.demo:
        quota = ", ".join(f"{k}: {v}" for k, v in ops.quota.items()) or "no quota header seen"
        blocked = ops.blocked
        sources[0] = {"name": "EPO Open Patent Services", "state": "off" if blocked else "read",
                      "label": "blocked" if blocked else "read",
                      "detail": (blocked or f"{ops.calls} calls. {quota}")}
    if bq is not None and not args.demo:
        for src in sources:
            if src["name"].startswith("Google BigQuery"):
                src["state"] = "off" if bq.error else "read"
                src["label"] = "error" if bq.error else "read"
                src["detail"] = bq.error or bq.stats()
    complete = bool((ops is not None or bq is not None) and not args.demo and not (ops is not None and ops.blocked)
                    and brands_out and not any(b["diag"]["errors"] for b in brands_out))
    results = {"complete": complete, "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "demo": bool(args.demo),
               "notes": notes, "sources": sources, "product_families": registry, "family_maps": family_maps,
               "new_product_families": fres["created"], "brands": brands_out}
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
