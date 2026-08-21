"""Per-player league data, aggregated from each match's standout performances.

WHAT THIS IS, EXACTLY - because it is easy to misread and the dashboard must not.

CricHeroes publishes a full scorecard only to its own client, and its tournament
leaderboard is behind a PRO subscription. What every match page *does* carry, in
the HTML, is `best_performances`: the top three batting and top three bowling
efforts of that match. That is what we collect, so for 86 matches we hold 258
batting and 258 bowling performances.

So these are NOT season averages. A player's runs here are the runs he scored in
the matches where he was among the three best batters - his quiet games are
absent, and so are the players who never had a standout day. Read as an average
it flatters everybody.

Read as a threat list it is exactly right, and that is the question scouting
actually asks: who has taken a match away from someone, how often, and how fast
they scored while doing it. Every label in the dashboard and every figure in the
fact pack is worded that way.
"""
import collections
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "league-raw" / "performances.tsv"


def _balls(overs):
    """CricHeroes writes overs as O.B - '2.4' is 2 overs and 4 balls, not 2.67."""
    try:
        s = str(overs)
        if "." in s:
            o, b = s.split(".", 1)
            return int(o) * 6 + int(b or 0)
        return int(float(s)) * 6
    except (ValueError, TypeError):
        return 0


def _num(v, cast=int, default=0):
    try:
        return cast(v)
    except (ValueError, TypeError):
        return default


def load_rows():
    if not SRC.exists():
        return []
    with SRC.open(encoding="utf-8") as fh:
        return [r for r in csv.reader(fh, delimiter="\t") if len(r) == 12]


def build_players():
    rows = load_rows()
    if not rows:
        return None

    bat = collections.defaultdict(lambda: dict(
        inns=0, runs=0, balls=0, fours=0, sixes=0, best=0, notout=0))
    bowl = collections.defaultdict(lambda: dict(
        inns=0, wkts=0, runs=0, balls=0, dots=0, maidens=0, bestW=0, bestR=0))

    for r in rows:
        kind, mid, _inn, team, name = r[0], r[1], r[2], r[3], r[4]
        key = (team, name)
        if kind == "B":
            runs, balls = _num(r[5]), _num(r[6])
            d = bat[key]
            d["inns"] += 1
            d["runs"] += runs
            d["balls"] += balls
            d["fours"] += _num(r[7])
            d["sixes"] += _num(r[8])
            d["notout"] += 1 if _num(r[10]) == 0 else 0
            if runs > d["best"]:
                d["best"] = runs
        else:
            wkts, runs, bl = _num(r[7]), _num(r[6]), _balls(r[5])
            d = bowl[key]
            d["inns"] += 1
            d["wkts"] += wkts
            d["runs"] += runs
            d["balls"] += bl
            d["dots"] += _num(r[9])
            d["maidens"] += _num(r[10])
            # best figures: most wickets, then fewest runs
            if wkts > d["bestW"] or (wkts == d["bestW"] and runs < d["bestR"]):
                d["bestW"], d["bestR"] = wkts, runs

    def bat_row(key, d):
        team, name = key
        return {
            "name": name, "team": team, "inns": d["inns"], "runs": d["runs"],
            "balls": d["balls"], "best": d["best"], "fours": d["fours"],
            "sixes": d["sixes"], "notout": d["notout"],
            "sr": round(d["runs"] / d["balls"] * 100, 1) if d["balls"] else None,
            "perInns": round(d["runs"] / d["inns"], 1) if d["inns"] else None,
        }

    def bowl_row(key, d):
        team, name = key
        ov = d["balls"] / 6 if d["balls"] else 0
        return {
            "name": name, "team": team, "inns": d["inns"], "wkts": d["wkts"],
            "runs": d["runs"], "balls": d["balls"],
            "overs": round(ov, 1), "dots": d["dots"], "maidens": d["maidens"],
            "econ": round(d["runs"] / ov, 2) if ov else None,
            "dotPct": round(d["dots"] / d["balls"] * 100, 1) if d["balls"] else None,
            "best": "%d-%d" % (d["bestW"], d["bestR"]),
        }

    batters = [bat_row(k, v) for k, v in bat.items()]
    bowlers = [bowl_row(k, v) for k, v in bowl.items()]

    teams = {}
    for t in sorted({r[3] for r in rows}):
        tb = sorted((b for b in batters if b["team"] == t),
                    key=lambda x: (-x["runs"], -x["best"]))
        tw = sorted((b for b in bowlers if b["team"] == t),
                    key=lambda x: (-x["wkts"], x["econ"] if x["econ"] is not None else 99))
        teams[t] = {
            "batters": tb[:6],
            "bowlers": tw[:6],
            "standoutInnings": sum(b["inns"] for b in tb),
            "standoutSpells": sum(b["inns"] for b in tw),
        }

    return {
        "matches": len({r[1] for r in rows}),
        "battingPerformances": sum(1 for r in rows if r[0] == "B"),
        "bowlingPerformances": sum(1 for r in rows if r[0] == "W"),
        "teams": teams,
        "leaders": {
            "batting": sorted(batters, key=lambda x: -x["runs"])[:10],
            "bowling": sorted(bowlers, key=lambda x: -x["wkts"])[:10],
            "bigHits": sorted(batters, key=lambda x: -x["sixes"])[:8],
        },
        "note": ("Top three batting and top three bowling performances of each "
                 "match. Not season averages - quiet games are not in here."),
    }


if __name__ == "__main__":
    import json
    d = build_players()
    print(json.dumps(d, indent=1)[:900] if d else "no data")
