"""Picks up a collector download, validates it, and rebuilds the dashboard.

    python3 tools/sync.py                    # takes the newest rcb-performances.tsv
    python3 tools/sync.py path.tsv           # or an explicit file
    python3 tools/sync.py path.tsv --force   # install even if matches are lost

It refuses to install a file that is worse than the one already in place -
fewer matches almost always means the collector was interrupted, and silently
replacing good data with a partial scrape is the one failure that would be hard
to notice later. Naming a file explicitly is NOT consent to lose data; only
--force is, and it names what it is about to drop before doing it.
"""
import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "league-raw" / "scorecards.tsv"
DOWNLOADS = Path.home() / "Downloads"


def read(path):
    with Path(path).open(encoding="utf-8") as fh:
        return [r for r in csv.reader(fh, delimiter="\t") if r]


def merge_add(new_path, dest):
    """Append a new competition's rows, replacing that competition if re-synced.

    Each competition arrives as its own file now, so a sync of one league must
    not wipe the others. Rows are keyed by competition id (third-from-last
    column); re-importing a competition replaces just its rows.
    """
    new = [r for r in csv.reader(open(new_path, encoding="utf-8"), delimiter="\t") if r]
    if not new:
        print("nothing in %s" % new_path)
        return None
    tid = new[0][-4]
    keep = []
    if dest.exists():
        keep = [r for r in csv.reader(dest.open(encoding="utf-8"), delimiter="\t")
                if r and r[-4] != tid]
    out = keep + new
    with dest.open("w", encoding="utf-8", newline="") as fh:
        csv.writer(fh, delimiter="\t").writerows(out)
    print("merged competition %s: %d new rows, %d kept -> %d total"
          % (tid, len(new), len(keep), len(out)))
    return out


def check(rows, label):
    # batting rows carry 13 fields, bowling rows 16 - a mismatch means a merged
    # or truncated line, which is how a missing trailing newline showed up once.
    want = {"B": 17, "W": 20}
    bad = [i for i, r in enumerate(rows, 1)
           if r[0] not in want or len(r) != want[r[0]]]
    matches = {r[1] for r in rows if len(r) > 1}
    teams = {r[3] for r in rows if len(r) > 3}
    unresolved = {t for t in teams if t.startswith("team")}
    if unresolved:
        print("    unresolved team ids: %s" % ", ".join(sorted(unresolved)[:5]))
    print("  %-9s %5d rows | %3d matches | %2d teams | %d malformed"
          % (label, len(rows), len(matches), len(teams), len(bad)))
    if bad:
        print("    malformed lines:", bad[:5])
    return matches, bad


def main():
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv
    if args:
        src = Path(args[0])
    else:
        found = sorted(DOWNLOADS.glob("rcb-scorecards*.tsv"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not found:
            print("No rcb-scorecards.tsv in ~/Downloads.")
            print("Run tools/collector.js in the browser first - see league-raw/README.md")
            return 1
        src = found[0]

    print("source: %s" % src)
    rows = read(src)
    if not rows:
        print("That file is empty; nothing installed.")
        return 1

    new_matches, bad = check(rows, "incoming")
    if bad:
        print("Refusing to install a file with malformed rows.")
        return 1

    if DEST.exists():
        old_matches, _ = check(read(DEST), "current")
        lost = old_matches - new_matches
        if lost:
            print("\nThe incoming file is MISSING %d match(es) the current one has:"
                  % len(lost))
            print("  %s" % ", ".join(sorted(lost)[:10])
                  + (" ..." if len(lost) > 10 else ""))
            if not force:
                print("That usually means the collector was interrupted. Nothing installed.")
                print("Re-run the collector, or pass --force to install anyway.")
                return 1
            print("--force given: installing anyway and dropping those matches.")
        gained = new_matches - old_matches
        if gained:
            print("\n  new matches: %s" % ", ".join(sorted(gained)))

    DEST.parent.mkdir(exist_ok=True)
    if src.resolve() != DEST.resolve():
        shutil.copy2(src, DEST)
        print("\ninstalled -> %s" % DEST.relative_to(ROOT))
    else:
        print("\nalready in place -> %s" % DEST.relative_to(ROOT))

    print("\nrebuilding...")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build.py")],
                       cwd=ROOT, capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode:
        return r.returncode

    print("\nNow commit and push to publish:")
    print('  git add -A && git commit -m "Sync league data" && git push')
    return 0


if __name__ == "__main__":
    sys.exit(main())
