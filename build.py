#!/usr/bin/env python3
"""Build dashboard.html by embedding research JSON into dashboard_template.html."""
import json, pathlib
from datetime import datetime, timezone

root = pathlib.Path(__file__).parent
research = root / "research"

# Brand list is config-driven (research/brands.json) so adding a new competitor
# to track never requires touching build.py or any other script.
brand_slugs = [b["slug"] for b in json.loads((research / "brands.json").read_text())["brands"]]
brands = [json.loads((research / f"{slug}.json").read_text()) for slug in brand_slugs
          if (research / f"{slug}.json").exists()]
gap = json.loads((research / "gap_analysis.json").read_text())
battles = json.loads((research / "battles.json").read_text())
insights_path = research / "product_insights.json"
insights = json.loads(insights_path.read_text()) if insights_path.exists() else None
summaries_path = research / "research_summaries.json"
summaries = json.loads(summaries_path.read_text()) if summaries_path.exists() else {}

# capability matrix: [status, footnote] where status is y/p/n
matrix = [
    {"cap": "Mesh group intercom", "Cardo": ["y", "DMC Gen2, 31 riders — review benchmark"], "Sena": ["y", "Mesh 3.0, 24 group / open unlimited"], "ASMAX": ["y", "brand-locked, 8-10 riders"], "Reso": ["y", "30 riders, brand-locked"]},
    {"cap": "Cellular / unlimited-range intercom", "Cardo": ["p", "VoIP in Mesh-Boost, unmarketed"], "Sena": ["y", "Wave (LTE), flagship feature"], "ASMAX": ["y", "CloudTalk, 50 riders"], "Reso": ["p", "software mesh via hotspot"]},
    {"cap": "AI voice assistant", "Cardo": ["n", "Natural Voice = commands only"], "Sena": ["n", "voice commands + AI noise calc"], "ASMAX": ["y", "Hi Max offline AI (EN/ES/JA)"], "Reso": ["p", "Hey RESO continuous listening"]},
    {"cap": "Crash detection / SOS", "Cardo": ["y", "Packtalk Pro IMU (region-limited)"], "Sena": ["n", ""], "ASMAX": ["n", ""], "Reso": ["y", "GNSS + gyro SOS at $359"]},
    {"cap": "IP67 waterproof (published)", "Cardo": ["y", "Packtalk line; entry lines unrated"], "Sena": ["p", "IPX7 60-series only"], "ASMAX": ["y", "even at $89.99"], "Reso": ["y", "both main models"]},
    {"cap": "Premium audio partner", "Cardo": ["y", "Sound by JBL 40/45mm"], "Sena": ["y", "Harman Kardon / Bose (EVO)"], "ASMAX": ["p", "Bongiovi tuning"], "Reso": ["p", "self-developed + Audio X"]},
    {"cap": "OTA feature updates", "Cardo": ["y", "Mesh-Boost added major features free"], "Sena": ["y", "app OTA"], "ASMAX": ["y", "FOTA"], "Reso": ["y", "Reso Link app"]},
    {"cap": "Universal cross-brand pairing", "Cardo": ["y", "bridges to any brand via BT"], "Sena": ["p", "MeshON pulls others into Sena mesh"], "ASMAX": ["p", "universal BT + CloudTalk app"], "Reso": ["n", "proprietary; weak mixed-group story"]},
    {"cap": "Action-camera audio integration", "Cardo": ["n", ""], "Sena": ["n", "(camera helmet instead)"], "ASMAX": ["p", "Insta360 wireless audio"], "Reso": ["y", "GoPro/DJI/Insta360 comms-in-footage"]},
    {"cap": "Mesh product under $250", "Cardo": ["n", "cheapest DMC moto unit $359.95"], "Sena": ["y", "Spider RT1 $199"], "ASMAX": ["y", "S1 $89.99"], "Reso": ["p", "Neo $269; ~$225 in SEA"]},
    {"cap": "Lifetime warranty", "Cardo": ["n", "3yr Edge/Pro, 2yr rest"], "Sena": ["y", "60S EVO main unit"], "ASMAX": ["n", "2yr"], "Reso": ["n", "3yr"]},
    {"cap": "Smart helmet line", "Cardo": ["y", "Beyond GT/GTS + Venture MX (2026)"], "Sena": ["y", "8 models incl. Phantom CAM 4K"], "ASMAX": ["n", "marketing only, none shipping"], "Reso": ["n", ""]},
    {"cap": "US retail / dealer distribution", "Cardo": ["y", "RevZilla, Cycle Gear install, dealers"], "Sena": ["y", "widest retail + OEM"], "ASMAX": ["p", "Amazon US only; AIMExpo push"], "Reso": ["n", "DTC website only"]},
    {"cap": "Tier-1 Western press coverage", "Cardo": ["y", "wins most 'best intercom' roundups"], "Sena": ["y", "MCN 4/5, iF Design awards"], "ASMAX": ["n", "regional/PR only"], "Reso": ["n", "SEA outlets only"]},
]

data = {"brands": brands, "gap": gap, "battles": battles, "insights": insights, "summaries": summaries, "built_at": datetime.now(timezone.utc).isoformat()}
tpl = (root / "dashboard_template.html").read_text()
out = tpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
(root / "dashboard.html").write_text(out)
(root / "index.html").write_text(out)  # same file at site root for GitHub Pages
print(f"dashboard.html + index.html written ({len(out):,} bytes)")
