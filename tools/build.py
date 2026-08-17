#!/usr/bin/env python3
"""Rebuilds ../index.html from tools/data.py + tools/template.html.

    python3 tools/build.py

Produces one self-contained file: no CDN, no fetch, no build step. It works
served from GitHub Pages and equally well opened straight off disk.
Output is pure ASCII, so it renders correctly no matter what charset a host sends.
"""
import json, sys, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from stats import build_payload

TITLE = "GTCC Fall League — Royal Challenger Blaster Match Dashboard"
DESC = ("Phase-by-phase targets, opponent scouting and a ten-point playbook, built from "
        "88 matches, all read ball by ball. The win line is 120; the death overs decide it.")


def to_entities(s):
    return ''.join(c if ord(c) < 128 else '&#%d;' % ord(c) for c in s)


def to_jsesc(s):
    return ''.join(c if ord(c) < 128 else '\\u%04x' % ord(c) for c in s)


def main():
    payload = build_payload()
    data = json.dumps(payload)          # ensure_ascii=True by default
    assert data.isascii()

    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    if "/*__DATA__*/" not in tpl:
        sys.exit("template.html is missing the /*__DATA__*/ placeholder")
    body = tpl.replace("/*__DATA__*/", data)

    # Character references are not decoded inside <script>, so escape the two
    # regions differently: \uXXXX in JS, numeric references in the markup.
    i, j = body.index("<script>"), body.index("</script>")
    body = to_entities(body[:i]) + to_jsesc(body[i:j]) + to_entities(body[j:])

    # The template carries its own <title>; the standalone page needs a full head.
    body = body.replace(f"<title>{to_entities(TITLE)}</title>", "", 1)
    built = datetime.date.today().isoformat()

    html = f"""<!doctype html>
<html lang="en" data-built="{built}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#F2F0E9" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#131614" media="(prefers-color-scheme: dark)">
<title>{to_entities(TITLE)}</title>
<meta name="description" content="{to_entities(DESC)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{to_entities(TITLE)}">
<meta property="og:description" content="{to_entities(DESC)}">
<meta name="twitter:card" content="summary">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><text y='14' font-size='14'>&#127951;</text></svg>">
</head>
<body>
{body}
</body>
</html>
"""
    assert html.isascii(), "output must be pure ASCII"
    out = ROOT / "index.html"
    out.write_text(html, encoding="utf-8")

    lg = payload["league"]
    print(f"built {out}  ({len(html):,} bytes)")
    print(f"  {lg['matches']} matches · {lg['teams']} teams · {lg['first']} to {lg['last']}")
    print(f"  bat-first {lg['batFirstPct']}% · avg 1st innings {lg['avg1']} · "
          f"120+ defended {lg['hi120']['w']}/{lg['hi120']['n']}")


if __name__ == "__main__":
    main()
