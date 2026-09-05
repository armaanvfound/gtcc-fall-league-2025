"""Per-team 2026 intel for the match plan: this season's form and players.

Built from league-raw/results-2026.tsv - the same harvest as the results, the
points table and the leaderboards, so one sync refreshes all of them together
and none can disagree.

What this holds per team, and what it deliberately cannot:

It HOLDS full player cards - every batter's runs/balls/boundaries and every
bowler's overs/runs/wickets/dot balls, per 2026 league match - plus team totals
with the batted-first/chased split. That is enough to say who their in-form
players are THIS season and how their totals run.

It CANNOT hold phase splits (powerplay/middle/death): those need ball-by-ball,
which CricHeroes only renders client-side per match, and we read it only for
our own games. So the match plan blends this file's 2026 form with the 2025
phase profiles - each labelled with its year - rather than pretending one
source does both jobs.

Players key on CricHeroes player_id, never on the name string (the (c)/(wk)
suffix split 61 players in the 2025 data).
"""
import collections
import csv
import re
from pathlib import Path

from results2026 import _canon

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "league-raw" / "results-2026.tsv"

US = "Royal Challenger Blaster"
ROLE_RE = re.compile(r"\s*\((c|wk|c\s*&\s*wk|wk\s*&\s*c)\)\s*$", re.I)


def _clean(name):
    return ROLE_RE.sub("", name or "").strip()


def _balls(overs):
    try:
        s = str(overs).strip()
        if "." in s:
            o, b = s.split(".", 1)
            return int(o) * 6 + int(b or 0)
        return int(float(s)) * 6
    except (ValueError, TypeError):
        return 0


def build_opponents2026():
    if not SRC.exists():
        return None

    matches = {}
    with SRC.open(encoding="utf-8") as fh:
        for r in csv.reader(fh, delimiter="\t"):
            if not r:
                continue
            m = matches.setdefault(r[1], {"innings": {}, "bat": [], "bowl": []})
            if r[0] == "M":
                m.update(date=r[2], winner=_canon(r[5]), margin=r[6])
            elif r[0] == "I":
                m["innings"][int(r[2])] = dict(
                    team=_canon(r[3]), runs=int(r[4]), wkts=int(r[5]),
                    overs=r[6], allOut=bool(int(r[8])) if len(r) > 8 else int(r[5]) >= 10)
            elif r[0] == "B" and len(r) >= 13:
                m["bat"].append(r)
            elif r[0] == "W" and len(r) >= 16:
                m["bowl"].append(r)

    teams = {}

    def team(name):
        return teams.setdefault(name, dict(
            played=0, won=0, results=[],
            batFirstTotals=[], chaseTotals=[],
            bat=collections.defaultdict(lambda: dict(
                runs=0, balls=0, inns=0, outs=0, fours=0, sixes=0, best=0,
                names=collections.Counter())),
            bowl=collections.defaultdict(lambda: dict(
                wkts=0, runs=0, balls=0, dots=0, inns=0,
                names=collections.Counter()))))

    for mid, m in matches.items():
        if len(m["innings"]) != 2:
            continue
        first, second = m["innings"][1], m["innings"][2]
        for inn, mine, other in ((1, first, second), (2, second, first)):
            t = team(mine["team"])
            t["played"] += 1
            won = m["winner"] == mine["team"]
            t["won"] += 1 if won else 0
            score = "%d%s" % (mine["runs"], " all out" if mine["allOut"] else "/%d" % mine["wkts"])
            t["results"].append(dict(
                date=m["date"], vs=other["team"], won=won, margin=m["margin"],
                us=score, them="%d/%d" % (other["runs"], other["wkts"]),
                battedFirst=inn == 1))
            (t["batFirstTotals"] if inn == 1 else t["chaseTotals"]).append(mine["runs"])
        for r in m["bat"]:
            d = team(_canon(r[3]))["bat"][r[12]]
            d["names"][_clean(r[4])] += 1
            d["inns"] += 1
            d["runs"] += int(r[5]); d["balls"] += int(r[6])
            d["fours"] += int(r[7]); d["sixes"] += int(r[8])
            how = (r[11] or "").strip().lower()
            if how and not how.startswith("not out") and not how.startswith("retired"):
                d["outs"] += 1
            d["best"] = max(d["best"], int(r[5]))
        for r in m["bowl"]:
            d = team(_canon(r[3]))["bowl"][r[15]]
            d["names"][_clean(r[4])] += 1
            bl = _balls(r[5])
            if not bl:
                continue
            d["inns"] += 1
            d["balls"] += bl; d["runs"] += int(r[7])
            d["wkts"] += int(r[8]); d["dots"] += int(r[9])

    out = {}
    for name, t in teams.items():
        bats = []
        for d in t["bat"].values():
            bats.append(dict(
                name=d["names"].most_common(1)[0][0], runs=d["runs"], balls=d["balls"],
                inns=d["inns"], best=d["best"], fours=d["fours"], sixes=d["sixes"],
                sr=round(d["runs"] / d["balls"] * 100, 1) if d["balls"] else None,
                avg=round(d["runs"] / d["outs"], 1) if d["outs"] else None))
        bowls = []
        for d in t["bowl"].values():
            bowls.append(dict(
                name=d["names"].most_common(1)[0][0], wkts=d["wkts"], runs=d["runs"],
                balls=d["balls"], inns=d["inns"],
                econ=round(d["runs"] / (d["balls"] / 6), 2) if d["balls"] else None,
                dotPct=round(d["dots"] / d["balls"] * 100, 1) if d["balls"] else None))
        bats.sort(key=lambda x: (-x["runs"], -(x["sr"] or 0)))
        bowls.sort(key=lambda x: (-x["wkts"], x["econ"] if x["econ"] is not None else 99))
        out[name] = dict(
            played=t["played"], won=t["won"],
            results=sorted(t["results"], key=lambda r: r["date"]),
            avgBatFirst=(round(sum(t["batFirstTotals"]) / len(t["batFirstTotals"]))
                         if t["batFirstTotals"] else None),
            avgChase=(round(sum(t["chaseTotals"]) / len(t["chaseTotals"]))
                      if t["chaseTotals"] else None),
            batters=bats[:5], bowlers=bowls[:5])

    return dict(
        teams=out,
        note=("This season's league form and player cards per team, from the full "
              "harvested scorecards. No phase splits here - those exist only for "
              "our own matches - so 2026 says WHO is scoring and HOW MUCH, while "
              "the 2025 profile still says WHEN in an innings a side scores."),
    )


if __name__ == "__main__":
    d = build_opponents2026()
    for name, t in sorted(d["teams"].items()):
        if name == US:
            continue
        print("%s  P%d W%d  batFirst avg %s  chase avg %s" % (
            name, t["played"], t["won"], t["avgBatFirst"], t["avgChase"]))
        for b in t["batters"][:2]:
            print("   BAT %-22s %3dr in %d inns @ SR %s" % (b["name"][:22], b["runs"], b["inns"], b["sr"]))
        for w in t["bowlers"][:2]:
            print("   BWL %-22s %dw, econ %s, dot%% %s" % (w["name"][:22], w["wkts"], w["econ"], w["dotPct"]))
