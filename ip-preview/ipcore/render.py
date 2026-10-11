from __future__ import annotations

import json
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "ip_preview_template.html"


def render(results: dict, template: Path = TEMPLATE) -> str:
    html = template.read_text(encoding="utf-8")
    payload = json.dumps(results, ensure_ascii=False)
    # keep the JSON from ending the script tag or breaking JS line rules
    payload = payload.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    marker = "/*__DATA__*/null"
    if marker not in html:
        raise ValueError("template marker not found")
    return html.replace(marker, payload, 1)
