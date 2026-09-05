#!/usr/bin/env python3
"""Install a fresh 2026 harvest and rebuild everything that hangs off it.

    python3 tools/sync2026.py            # newest rcb-results-2026*.tsv in ~/Downloads
    python3 tools/sync2026.py FILE       # or an explicit file
    python3 tools/sync2026.py --force    # accept fewer matches than installed

The browser saves repeat downloads as "rcb-results-2026 (1).tsv", "(2)" and so
on, so the newest file BY MODIFIED TIME is taken, never by name - installing the
bare-named file once shipped a stale harvest while the real one sat beside it
with " (1)" in its name.

One file feeds four things: the season page's results, the computed points
table, the fact pack's results + standings blocks, and (through group tallies)
the qualification picture. Rebuilding here refreshes all of them together, which
is the point - they can never disagree.

After it passes, publish:  git add -A && git commit -m "2026 sync" && git push
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEST = ROOT / "league-raw" / "results-2026.tsv"
DOWNLOADS = Path.home() / "Downloads"

# row type -> exact column count; I rows carry the is_allout flag (9th column)
SHAPE = {"M": 8, "I": 9, "B": 13, "W": 16}


def check(path):
    """Validate shape and return the set of match ids, or None with a message."""
    mids = set()
    bad = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        f = line.split("\t")
        want = SHAPE.get(f[0])
        if want is None or len(f) != want:
            bad.append((n, f[0], len(f)))
        elif f[0] == "M":
            mids.add(f[1])
    if bad:
        for n, kind, got in bad[:5]:
            print("  line %d: %s row has %d columns (want %s)" %
                  (n, kind, got, SHAPE.get(kind, "?")))
        print("REFUSED: %d malformed rows. Harvest again with tools/collect2026.js -" % len(bad))
        print("an old collector without the all-out column also fails this check on purpose.")
        return None
    return mids


def main():
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--force"]
    if args:
        src = Path(args[0])
    else:
        found = sorted(DOWNLOADS.glob("rcb-results-2026*.tsv"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not found:
            print("No rcb-results-2026*.tsv in ~/Downloads.")
            print("Run tools/collect2026.js on any cricheroes.com page first.")
            return 1
        src = found[0]
        print("newest download: %s" % src.name)

    mids = check(src)
    if mids is None:
        return 1

    old = check(DEST) if DEST.exists() else set()
    if old and len(mids) < len(old) and not force:
        print("REFUSED: new file has %d matches, installed has %d." % (len(mids), len(old)))
        print("A partial harvest would silently delete results. --force overrides.")
        return 1

    DEST.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print("installed %d matches (%+d) -> %s" % (len(mids), len(mids) - len(old),
                                                DEST.relative_to(ROOT)))

    print("\nrebuilding...")
    r = subprocess.run([sys.executable, str(HERE / "build.py")], cwd=ROOT)
    if r.returncode:
        return r.returncode

    sys.path.insert(0, str(HERE))
    from standings2026 import build_standings2026
    st = build_standings2026()
    if st:
        print("\nGroup 5:")
        for row in st["groups"]["Group 5"]:
            print("  %-28s P%d  %2dpts  NRR %s" % (
                row["team"][:28], row["played"], row["points"],
                ("%+.2f" % row["nrr"]) if row["nrr"] is not None else "-"))

    print('\nNow publish:  git add -A && git commit -m "2026 sync" && git push')
    return 0


if __name__ == "__main__":
    sys.exit(main())
