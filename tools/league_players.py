"""Per-player league stats, from the full scorecard of every match.

Each CricHeroes match page embeds `scoreCardData`: both innings complete - every
batter with runs, balls, boundaries, batting hand and how they got out, and every
bowler with overs, maidens, runs, wickets, dots, boundaries conceded and extras.
tools/collector.js harvests it; this turns it into per-player and per-team stats.

These ARE real season figures - every innings by every player, not a highlight
reel - so averages, strike rates and economies here mean what they normally mean.
The only caveat worth carrying is sample size, which is why every row keeps its
innings count and the pages rank on volume before rate.

Note there are no LBWs anywhere in this data - these are tennis-ball matches and
the law is not applied. Caught is 76% of dismissals, which is why fielding
placement is the lever here, not trapping people in front.

`how_out` is the batter's dismissal string, e.g. "c Santosh Natarajan b Gopal
Kanniappan". It gives dismissal type and, where relevant, the bowler credited -
so we can say how a batter usually gets out, which is the scouting question.
"""
import collections
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "league-raw" / "scorecards.tsv"

MIN_BAT_INNS = 3      # below this a strike rate is noise
MIN_BOWL_INNS = 3


def _balls(overs):
    """Overs are written O.B - '2.4' is 2 overs and 4 balls, not 2.67."""
    try:
        s = str(overs).strip()
        if "." in s:
            o, b = s.split(".", 1)
            return int(o) * 6 + int(b or 0)
        return int(float(s)) * 6
    except (ValueError, TypeError):
        return 0


def _n(v, cast=int, default=0):
    try:
        return cast(v)
    except (ValueError, TypeError):
        return default


def dismissal(how):
    """Classify a dismissal string into a bucket, and pull out the bowler."""
    h = (how or "").strip()
    if not h or h.lower().startswith("not out"):
        return None, None
    low = h.lower()
    if low.startswith("retired"):
        return None, None
    if low.startswith("run out"):
        return "run out", None
    bowler = None
    m = re.search(r"\bb\s+(.+)$", h)
    if m:
        bowler = m.group(1).strip()
    if low.startswith("c&b") or low.startswith("c & b"):
        return "caught", bowler
    if low.startswith("c "):
        return "caught", bowler
    if low.startswith("st "):
        return "stumped", bowler
    if low.startswith("lbw"):
        return "lbw", bowler
    if low.startswith("b "):
        return "bowled", bowler
    if low.startswith("hit wicket") or low.startswith("hit wkt"):
        return "hit wicket", bowler
    return "other", bowler


def load_rows():
    if not SRC.exists():
        return []
    with SRC.open(encoding="utf-8") as fh:
        return [r for r in csv.reader(fh, delimiter="\t") if r]


def build_players():
    rows = load_rows()
    if not rows:
        return None

    bat = collections.defaultdict(lambda: dict(
        inns=0, runs=0, balls=0, fours=0, sixes=0, best=0, notout=0,
        ducks=0, fifties=0, hand=collections.Counter(),
        outs=collections.Counter(), matches=set()))
    bowl = collections.defaultdict(lambda: dict(
        inns=0, wkts=0, runs=0, balls=0, dots=0, maidens=0,
        fours=0, sixes=0, wides=0, noballs=0, bestW=0, bestR=999, matches=set()))

    for r in rows:
        if r[0] == "B" and len(r) == 13:
            _, mid, _inn, team, name, runs, balls, f4, f6, _sr, hand, how, _pid = r
            d = bat[(team, name)]
            d["inns"] += 1
            d["matches"].add(mid)
            d["runs"] += _n(runs)
            d["balls"] += _n(balls)
            d["fours"] += _n(f4)
            d["sixes"] += _n(f6)
            if hand:
                d["hand"][hand] += 1
            kind, _b = dismissal(how)
            if kind is None:
                d["notout"] += 1
            else:
                d["outs"][kind] += 1
            if _n(runs) > d["best"]:
                d["best"] = _n(runs)
            if _n(runs) == 0 and kind is not None:
                d["ducks"] += 1
            if _n(runs) >= 50:
                d["fifties"] += 1
        elif r[0] == "W" and len(r) == 16:
            _, mid, _inn, team, name, ov, md, runs, wk, dots, f4, f6, wd, nb, _er, _pid = r
            d = bowl[(team, name)]
            bl = _balls(ov)
            if bl == 0:
                continue
            d["inns"] += 1
            d["matches"].add(mid)
            d["balls"] += bl
            d["runs"] += _n(runs)
            d["wkts"] += _n(wk)
            d["dots"] += _n(dots)
            d["maidens"] += _n(md)
            d["fours"] += _n(f4)
            d["sixes"] += _n(f6)
            d["wides"] += _n(wd)
            d["noballs"] += _n(nb)
            if _n(wk) > d["bestW"] or (_n(wk) == d["bestW"] and _n(runs) < d["bestR"]):
                d["bestW"], d["bestR"] = _n(wk), _n(runs)

    def bat_row(key, d):
        team, name = key
        outs = sum(d["outs"].values())
        top = d["outs"].most_common(1)
        return {
            "name": name, "team": team, "inns": d["inns"], "runs": d["runs"],
            "balls": d["balls"], "best": d["best"], "fours": d["fours"],
            "sixes": d["sixes"], "notout": d["notout"], "ducks": d["ducks"],
            "fifties": d["fifties"],
            "hand": d["hand"].most_common(1)[0][0] if d["hand"] else None,
            "avg": round(d["runs"] / outs, 1) if outs else None,
            "sr": round(d["runs"] / d["balls"] * 100, 1) if d["balls"] else None,
            "boundaryPct": round((d["fours"] * 4 + d["sixes"] * 6) / d["runs"] * 100, 1)
                           if d["runs"] else None,
            "usuallyOut": top[0][0] if top else None,
            "usuallyOutPct": round(top[0][1] / outs * 100) if top and outs else None,
        }

    def bowl_row(key, d):
        team, name = key
        ov = d["balls"] / 6
        return {
            "name": name, "team": team, "inns": d["inns"], "wkts": d["wkts"],
            "runs": d["runs"], "balls": d["balls"], "overs": round(ov, 1),
            "dots": d["dots"], "maidens": d["maidens"],
            "fours": d["fours"], "sixes": d["sixes"],
            "extras": d["wides"] + d["noballs"],
            "econ": round(d["runs"] / ov, 2) if ov else None,
            "avg": round(d["runs"] / d["wkts"], 1) if d["wkts"] else None,
            "sr": round(d["balls"] / d["wkts"], 1) if d["wkts"] else None,
            "dotPct": round(d["dots"] / d["balls"] * 100, 1) if d["balls"] else None,
            "best": "%d-%d" % (d["bestW"], d["bestR"]) if d["bestR"] < 999 else "-",
        }

    batters = [bat_row(k, v) for k, v in bat.items()]
    bowlers = [bowl_row(k, v) for k, v in bowl.items()]

    teams = {}
    for t in sorted({r[3] for r in rows if r}):
        tb = [b for b in batters if b["team"] == t]
        tw = [b for b in bowlers if b["team"] == t]
        # rank on weight of runs/wickets, not on a rate off two innings
        tb.sort(key=lambda x: (-x["runs"], -(x["sr"] or 0)))
        tw.sort(key=lambda x: (-x["wkts"], x["econ"] if x["econ"] is not None else 99))
        lhb = sum(1 for b in tb if b["hand"] == "LHB")
        teams[t] = {
            "batters": tb[:6],
            "bowlers": tw[:6],
            "squadSeen": len(tb),
            "leftHanders": lhb,
            "rightHanders": sum(1 for b in tb if b["hand"] == "RHB"),
        }

    qual_b = [b for b in batters if b["inns"] >= MIN_BAT_INNS]
    qual_w = [w for w in bowlers if w["inns"] >= MIN_BOWL_INNS]
    return {
        "matches": len({r[1] for r in rows if r}),
        "battingInnings": sum(1 for r in rows if r and r[0] == "B"),
        "bowlingSpells": sum(1 for r in rows if r and r[0] == "W"),
        "playersSeen": len(batters),
        "minInns": {"bat": MIN_BAT_INNS, "bowl": MIN_BOWL_INNS},
        "teams": teams,
        "leaders": {
            "runs": sorted(batters, key=lambda x: -x["runs"])[:10],
            "wickets": sorted(bowlers, key=lambda x: -x["wkts"])[:10],
            "strikeRate": sorted(qual_b, key=lambda x: -(x["sr"] or 0))[:10],
            "economy": sorted(qual_w, key=lambda x: (x["econ"] if x["econ"] is not None else 99))[:10],
            "sixes": sorted(batters, key=lambda x: -x["sixes"])[:10],
        },
        "note": ("Every innings of every match - real season figures. Rates for "
                 "leaderboards need %d innings; team tables rank on volume first."
                 % MIN_BAT_INNS),
    }


if __name__ == "__main__":
    import json
    d = build_players()
    print(json.dumps({k: v for k, v in d.items() if k != "teams"}, indent=1)[:700] if d else "no data")
