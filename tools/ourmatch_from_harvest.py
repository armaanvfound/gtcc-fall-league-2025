"""Keeps our-matches/ in step with the season harvest, on every build.

Our own match files feed the Our form page, and they used to be written by
hand - so a sync could refresh the points table while Our form still showed an
old record. It happened: two league defeats sat in the harvest for a week while
Our form said 1-0 and +1.39 and The season said 1-2 and -1.70.

So every build now derives a scorecard-level file for any Royal Challenger
Blaster league match in league-raw/results-2026.tsv that has no file yet: both
innings' totals, the all-out state, the extras split (wides and no-balls summed
from the bowling side's cards, byes as the remainder), every batter and every
one of our bowlers. The record, net run rate and player careers are complete
from that alone, and the file is refused unless it reconciles to the card.

What a scorecard cannot give is WHEN the runs came, so the phase fields stay
null until tools/capture_commentary.js reads the ball-by-ball; the pages say so
for that match. An existing file is never overwritten - it may carry phases.
"""
import csv
import json
import re
from pathlib import Path

from results2026 import US, _canon

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "league-raw" / "results-2026.tsv"
DEST = ROOT / "our-matches"

ROLE_RE = re.compile(r"\s*\((c|wk|c\s*&\s*wk|wk\s*&\s*c)\)\s*$", re.I)


def _clean(name):
    return ROLE_RE.sub("", name or "").strip()


def _balls(overs):
    """Cricket overs are O.B - '0.5' is five balls, not half an over."""
    s = str(overs).strip()
    if "." in s:
        o, b = s.split(".", 1)
        return int(o) * 6 + int(b or 0)
    return int(float(s)) * 6


def _slug(team):
    return re.sub(r"[^a-z0-9]+", "-", (team or "").lower()).strip("-")


def _toss(raw):
    m = re.match(r"\s*Toss:\s*(.+?)\s+opt to\s+(bat|field|bowl)", raw or "", re.I)
    if not m:
        return raw or ""
    return "%s won the toss and chose to %s" % (_canon(m.group(1)), m.group(2).lower())


def _load():
    matches = {}
    with SRC.open(encoding="utf-8") as fh:
        for r in csv.reader(fh, delimiter="\t"):
            if not r:
                continue
            m = matches.setdefault(r[1], {"M": None, "I": [], "B": [], "W": []})
            if r[0] == "M":
                m["M"] = r
            elif r[0] in ("I", "B", "W"):
                m[r[0]].append(r)
    return matches


def _innings(m, row):
    n = row[2]
    runs, wkts, extras = int(row[4]), int(row[5]), int(row[7])
    flag = bool(int(row[8])) if len(row) > 8 else False
    # bowling rows are filed under the innings they were bowled in
    bowl = [w for w in m["W"] if w[2] == n]
    wides = sum(int(w[12] or 0) for w in bowl)
    nbs = sum(int(w[13] or 0) for w in bowl)
    return dict(
        order=int(n), team=_canon(row[3]), runs=runs, wkts=wkts,
        oversText=row[6], balls=_balls(row[6]),
        wideRuns=wides, noBalls=nbs, byeRuns=max(0, extras - wides - nbs),
        # ten down is all out whatever the flag says; CricHeroes has left it
        # unset on an innings that was plainly bowled out, and NRR hangs on it
        allOut=flag or wkts >= 10,
        phases=None,
        _extras=extras,
        _bat=[b for b in m["B"] if b[2] == n],
        _bowl=bowl,
    )


def _build(mid, m):
    rows = sorted(m["I"], key=lambda r: int(r[2]))
    a, b = _innings(m, rows[0]), _innings(m, rows[1])
    us, them = (a, b) if a["team"] == US else (b, a)

    batting = []
    for x in us["_bat"]:
        how = (x[11] or "").strip().lower()
        out = bool(how) and not how.startswith("not out") and not how.startswith("retired")
        batting.append([_clean(x[4]), int(x[5]), int(x[6]), int(x[7]), int(x[8]), out])

    our_bowling = {}
    for w in them["_bowl"]:
        our_bowling[_clean(w[4])] = dict(
            o=float(w[5]), balls=_balls(w[5]), r=int(w[7]), w=int(w[8]),
            dots=int(w[9] or 0), ph=None)

    # refuse anything that does not reconcile to the published card
    problems = []
    if sum(x[1] for x in batting) + us["_extras"] != us["runs"]:
        problems.append("our batting + extras != our total")
    if sum(v["r"] for v in our_bowling.values()) + them["byeRuns"] != them["runs"]:
        problems.append("our bowling runs + byes != their total")
    if sum(v["balls"] for v in our_bowling.values()) != them["balls"]:
        problems.append("our bowlers' balls != their innings")
    if problems:
        return None, problems

    M = m["M"]
    winner = _canon(M[5])
    for inn in (us, them):
        for k in ("_extras", "_bat", "_bowl", "team"):
            inn.pop(k)
    us["batting"] = batting
    us["battingPhases"] = {}
    them["ourBowling"] = our_bowling
    return dict(
        mid=mid, date=M[2], opp=_canon(rows[0][3]) if _canon(rows[0][3]) != US else _canon(rows[1][3]),
        venue=M[3], competition="GTCC Fall League 2026", isLeague=True,
        quota=15, phaseBounds=[5, 10],
        toss=_toss(M[4]),
        result="won" if winner == US else ("lost" if winner else "tied"),
        margin=M[6],
        url="https://cricheroes.com/scorecard/%s/gtcc-fall-league-2026/%s-vs-%s/scorecard"
            % (mid, _slug(rows[0][3]), _slug(rows[1][3])),
        phaseSource="scorecard only - phases fill in when tools/capture_commentary.js reads the ball-by-ball",
        ourInnings=us, theirInnings=them,
    ), []


def ensure_our_matches(verbose=True):
    """Write a file for every RCB league match the harvest has and we do not.
    Returns (created, refused) lists of match ids."""
    if not SRC.exists():
        return [], []
    created, refused = [], []
    for mid, m in _load().items():
        if not m["M"] or len(m["I"]) != 2:
            continue
        if US not in (_canon(r[3]) for r in m["I"]):
            continue
        path = DEST / ("%s.json" % mid)
        if path.exists():
            continue
        doc, problems = _build(mid, m)
        if doc is None:
            refused.append(mid)
            if verbose:
                print("our-matches: REFUSED %s - %s" % (mid, "; ".join(problems)))
            continue
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        created.append(mid)
        if verbose:
            print("our-matches: added %s (%s v %s, %s) - scorecard level, phases pending"
                  % (mid, doc["date"], doc["opp"], doc["result"]))
    return created, refused


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    c, r = ensure_our_matches()
    print("created %d, refused %d" % (len(c), len(r)))
