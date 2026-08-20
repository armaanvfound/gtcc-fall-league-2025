#!/usr/bin/env python3
"""Builds the dashboard's pages from tools/data.py + tools/template.html.

    python3 tools/build.py

One template holds every section and every script block; PAGES below says which
of them each page gets. A section is claimed by id, a script block by the
comment that opens it, so moving something between pages is a one-line edit here
rather than a copy-paste between files.

Each page also carries only the slice of the payload it uses. That is what keeps
them small as the season goes on: the league pages never ship our ball-by-ball
data, and the form page never ships 88 match logs.

Output is pure ASCII, so it renders correctly no matter what charset a host
sends, and every page is self-contained: no CDN, no fetch, no build step at read
time. They work served from GitHub Pages and equally well opened off disk.
"""
import json, re, sys, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from stats import build_payload

SITE = "GTCC Fall League 2026 - Royal Challenger Blaster"

# Deployed team proxy for the assistant (see worker/README.md). Paste the URL
# wrangler prints, then rebuild: the whole team shares one key and readers only
# ever enter a passphrase. While this is empty the assistant shows setup notes
# instead. No API key belongs here - the proxy holds it as a Cloudflare secret.
ASK_PROXY = "https://rcb-ask.rcb-ask.workers.dev"

# file -> what it is made of.
#   sections: <section id="..."> blocks, in the order given
#   js:       script blocks, named by the comment that opens them
#   data:     top-level payload keys this page needs
#   nav:      in-page jump links, as (label, element id)
PAGES = {
    "index": dict(
        title="Match plan",
        eyebrow="Royal Challenger Blaster &middot; GTCC Fall League 2026",
        h1="What to do on the day",
        desc=("Our 2026 fixtures and a match plan for each of them: the toss call, the target, "
              "and the phase-by-phase read on whoever we are playing."),
        sections=["season", "plan"],
        js=["01 - our 2026 campaign", "08 - match plan + opponent scouting"],
        data=["league", "phases", "season", "ours"],
        nav=[("Fixtures", "season"), ("Match plan", "plan")],
        footHide=("form",),   # section 01 already carries a full card for it
    ),
    "form": dict(
        title="Our form",
        eyebrow="Royal Challenger Blaster &middot; Our matches",
        h1="Our form so far",
        desc=("Every match Royal Challenger Blaster has played, read ball by ball: phase splits, "
              "dot-ball percentages, player careers and what they say we should change."),
        sections=["ours", "squad"],
        js=["02 - how we have actually played", "11 - squad"],
        data=["ours", "phases", "squad", "league"],
        nav=[("Match log", "ours"), ("Squad", "squad")],
    ),
    "league": dict(
        title="The league",
        eyebrow="GTCC Fall League &middot; 2025 season, read in full",
        h1="How this league is actually won",
        desc=("Phase-by-phase targets, opponent scouting and a ten-point playbook, built from 88 "
              "matches and every one of them read ball by ball. The win line is 120."),
        sections=["winline", "batfirst", "wickets", "teamlookup", "qualify", "sec-ranks",
                  "phases", "conditions", "playbook", "sources"],
        js=["01 - win line", "02 - bat first", "03 - wickets in hand", "05 - groups",
            "06 - ranks", "04 - team picker", "07 - phases",
            "09 - conditions", "10 - playbook", "12 - method"],
        data=["league", "teams", "phases", "ours"],
        nav=[("Win line", "winline"), ("Phase targets", "phases"), ("Playbook", "playbook"),
             ("Rankings", "sec-ranks"), ("Groups", "qualify"), ("Conditions", "conditions"),
             ("Sources", "sources")],
    ),
}

# Script blocks every page needs: the shared head (helpers) is handled separately.
ALWAYS_JS = ["provenance", "tooltips", "ask the data"]


def to_entities(s):
    return ''.join(c if ord(c) < 128 else '&#%d;' % ord(c) for c in s)


def to_jsesc(s):
    return ''.join(c if ord(c) < 128 else '\\u%04x' % ord(c) for c in s)


def split_template(tpl):
    """Pull the template apart into style, header, sections and script blocks."""
    style = re.search(r'<style>.*?</style>', tpl, re.S).group(0)
    topnav = re.search(r'<nav class="topnav".*?</nav>\n', tpl, re.S).group(0)
    header = re.search(r'<header>.*?</header>', tpl, re.S).group(0)
    # Page chrome that lives outside every <section>: the footer (inside .wrap)
    # and the hover tooltip element (page level). Both belong on every page.
    footer = re.search(r'<footer id="foot"></footer>', tpl).group(0)
    tip = re.search(r'<div id="tip"[^>]*></div>', tpl, re.S).group(0)
    # The assistant's markup is nested, so it is delimited by comments rather than
    # matched structurally. Anything outside a <section> has to be claimed here or
    # it is silently dropped from every page.
    ask = re.search(r'<!--ASK-->.*?<!--/ASK-->', tpl, re.S).group(0)
    tip = tip + "\n" + ask

    sections = {}
    for m in re.finditer(r'<section id="([^"]+)">.*?</section>', tpl, re.S):
        sections[m.group(1)] = m.group(0)

    script = re.search(r'<script>(.*?)</script>', tpl, re.S).group(1)
    # Everything before the first column-0 block comment is the shared head.
    parts = re.split(r'\n(?=/\* )', script)
    head, blocks = parts[0], {}
    for p in parts[1:]:
        name = re.match(r'/\* (.*?) \*/', p, re.S)
        if not name:
            continue
        # normalise the dashes so PAGES can be written in plain ASCII, and key on
        # the part before any colon so a block can carry a longer explanation
        key = name.group(1).replace('—', '-').replace('–', '-').strip()
        blocks[key] = p
        short = key.split(':')[0].strip()
        if short != key:
            blocks[short] = p
    return style, topnav, header, sections, head, blocks, footer, tip


def slice_payload(payload, keys):
    return {k: payload[k] for k in keys if k in payload}


def renumber(section_html, n):
    """Rewrite a section's sechead counter to its position on this page.

    The numbers in the template are the old single-page reading order; once the
    sections are spread across pages that order is meaningless and reads as a
    scatter of gaps (03, then 11, then 14). Each page counts its own from 01.
    """
    return re.sub(r'(<div class="n">)\d+(</div>)', r'\g<1>%02d\g<2>' % n,
                  section_html, count=1)


def main():
    payload = build_payload()
    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    style, topnav, header, sections, jshead, blocks, footer, tip = split_template(tpl)

    missing = []
    for name, cfg in PAGES.items():
        missing += [("section", name, s) for s in cfg["sections"] if s not in sections]
        missing += [("js", name, j) for j in cfg["js"] if j not in blocks]
    missing += [("js", "*", j) for j in ALWAYS_JS if j not in blocks]
    if missing:
        sys.exit("template is missing:\n" + "\n".join("  %s %s: %s" % m for m in missing))

    # A block can be registered under both its full name and a short alias, so
    # compare by the block text rather than by key or every alias reads as unused.
    claimed_text = {blocks[j] for j in ALWAYS_JS}
    for cfg in PAGES.values():
        claimed_text |= {blocks[j] for j in cfg["js"]}
    orphan_js = sorted({k for k, v in blocks.items() if v not in claimed_text})
    orphan_sec = sorted(set(sections) - {s for c in PAGES.values() for s in c["sections"]})

    # The chatbot's brief. Written next to the pages and fetched by the widget at
    # runtime, so one copy serves all three and adding a match refreshes the bot.
    try:
        from factpack import build_factpack
        facts = json.dumps(build_factpack(payload), separators=(",", ":"))
        (ROOT / "facts.json").write_text(facts, encoding="utf-8")
        facts_note = "facts.json  %7s bytes  (~%d tokens)" % (
            format(len(facts), ","), len(facts) / 3.5)
    except Exception as e:
        facts_note = "facts.json NOT written: %s" % e

    built = datetime.date.today().isoformat()
    for name, cfg in PAGES.items():
        data = json.dumps(slice_payload(payload, cfg["data"]))
        assert data.isascii()

        qnav = ''.join('<a href="#%s">%s</a>' % (i, lbl) for lbl, i in cfg["nav"])
        head = (header
                .replace("/*__EYEBROW__*/", cfg["eyebrow"])
                .replace("/*__H1__*/", cfg["h1"])
                .replace('<nav class="qnav" id="qnav" aria-label="Jump to section"></nav>',
                         '<nav class="qnav" aria-label="Jump to section">%s</nav>' % qnav))
        nav = topnav.replace('data-pg="%s"' % name, 'data-pg="%s" class="on" aria-current="page"' % name)

        # Every page ends with a way on to the others. index already carries a
        # richer, data-filled card for the form page, so it is not repeated here.
        others = [p for p in PAGES if p != name and p not in cfg.get("footHide", ())]
        foot = ('<nav class="pagefoot" aria-label="Other pages">' +
                ''.join('<a href="%s.html"><span class="pf-l">%s</span>'
                        '<span class="pf-h">%s</span><span class="pf-p">%s</span></a>'
                        % (p, PAGES[p]["title"], PAGES[p]["h1"], PAGES[p]["desc"])
                        for p in others) + '</nav>') if others else ''

        # The top nav is full-bleed so its sticky bar and border span the viewport
        # (its own .tn-in centres the links). Everything else lives inside .wrap,
        # which supplies the max-width column, the horizontal padding and the
        # centring — without it every page renders edge to edge.
        numbered = [renumber(sections[s], i) for i, s in enumerate(cfg["sections"], 1)]
        inner = head + "\n\n" + "\n\n".join(numbered) + "\n\n" + foot + "\n" + footer
        body = nav + '\n<div class="wrap">\n' + inner + "\n</div>\n" + tip
        js = jshead + "\n" + "\n".join(
            blocks[b] for b in cfg["js"] + [j for j in ALWAYS_JS if j not in cfg["js"]])
        js = (js.replace("/*__DATA__*/", data)
                .replace("/*__PAGE__*/", name)
                .replace("/*__ASKPROXY__*/", ASK_PROXY))

        # Character references are not decoded inside <script>, so the two regions
        # are escaped differently: numeric references in the markup, \uXXXX in JS.
        page = to_entities(style + "\n" + body) + "\n<script>\n" + to_jsesc(js) + "\n</script>"
        title = "%s - %s" % (cfg["title"], SITE)
        html = f"""<!doctype html>
<html lang="en" data-built="{built}" data-page="{name}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#F2F0E9" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#131614" media="(prefers-color-scheme: dark)">
<title>{to_entities(title)}</title>
<meta name="description" content="{to_entities(cfg['desc'])}">
<meta property="og:type" content="article">
<meta property="og:title" content="{to_entities(title)}">
<meta property="og:description" content="{to_entities(cfg['desc'])}">
<meta name="twitter:card" content="summary">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><text y='14' font-size='14'>&#127951;</text></svg>">
</head>
<body>
{page}
</body>
</html>
"""
        assert html.isascii(), "output must be pure ASCII"
        out = ROOT / ("%s.html" % name)
        out.write_text(html, encoding="utf-8")
        print("built %-12s %7s bytes  (%d sections, %d payload keys)" % (
            out.name, format(len(html), ','), len(cfg["sections"]), len(cfg["data"])))

    print("built " + facts_note)
    lg = payload["league"]
    print("  %d matches | %d teams | %s to %s" % (lg['matches'], lg['teams'], lg['first'], lg['last']))
    if payload.get("ours"):
        r = payload["ours"]["record"]
        print("  our record %dW %dL %dT in %d | NRR %+.2f" % (
            r['won'], r['lost'], r['tied'], r['played'], r['nrr']))
    if orphan_js:
        print("  note: script blocks on no page: " + ", ".join(orphan_js))
    if orphan_sec:
        print("  note: sections on no page: " + ", ".join(orphan_sec))


if __name__ == "__main__":
    main()
