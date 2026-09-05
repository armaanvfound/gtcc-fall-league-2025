"""Tournament leaderboards for the 2026 league, computed from our own harvest.

CricHeroes has leaderboards, but they are unreachable on a sync (Cloudflare
challenge on every fresh path, and the stats tabs sat behind CricHeroes PRO all
last season). They are also unnecessary: every completed match's full batting
and bowling card is already in league-raw/results-2026.tsv, and a leaderboard is
arithmetic over those - same story as the points table. Computing our own keeps
it on the same one-word sync and lets it say things CricHeroes never would:
which of the names are ours, and which play in our group.

Players are keyed on CricHeroes player_id, never on name - a captain arrives as
"Kushal Reddy  (c)" in the matches he captains and splits into two part-players
if you key on the string (61 players did exactly that in the 2025 data).

Early-season boards rank on volume (runs, wickets) outright; the rate boards
(strike rate, economy) carry a minimum sample so a six-ball cameo cannot top
them, and every row shows the innings it rests on.
"""
import collections
import csv
import re
from pathlib import Path

from results2026 import GROUPS, _canon

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "league-raw" / "results-2026.tsv"

US = "Royal Challenger Blaster"
OUR_GROUP = "Group 5"

MIN_SR_BALLS = 15      # rate boards only; volume boards have no floor
MIN_ECON_BALLS = 18

ROLE_RE = re.compile(r"\s*\((c|wk|c\s*&\s*wk|wk\s*&\s*c)\)\s*$", re.I)


def _clean_name(name):
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


def _group_of(team):
    for g, members in GROUPS.items():
        if team in members:
            return g
    return None


def build_leaders2026():
    if not SRC.exists():
        return None

    bat = collections.defaultdict(lambda: dict(
        runs=0, balls=0, inns=0, outs=0, fours=0, sixes=0, best=0,
        names=collections.Counter(), teams=collections.Counter()))
    bowl = collections.defaultdict(lambda: dict(
        wkts=0, runs=0, balls=0, dots=0, inns=0, bestW=-1, bestR=10**9,
        names=collections.Counter(), teams=collections.Counter()))
    n_matches = set()

    with SRC.open(encoding="utf-8") as fh:
        for r in csv.reader(fh, delimiter="\t"):
            if not r:
                continue
            if r[0] == "M":
                n_matches.add(r[1])
            elif r[0] == "B" and len(r) >= 13:
                d = bat[r[12]]
                d["names"][_clean_name(r[4])] += 1
                d["teams"][_canon(r[3])] += 1
                d["inns"] += 1
                d["runs"] += int(r[5]); d["balls"] += int(r[6])
                d["fours"] += int(r[7]); d["sixes"] += int(r[8])
                how = (r[11] or "").strip().lower()
                if how and not how.startswith("not out") and not how.startswith("retired"):
                    d["outs"] += 1
                d["best"] = max(d["best"], int(r[5]))
            elif r[0] == "W" and len(r) >= 16:
                d = bowl[r[15]]
                d["names"][_clean_name(r[4])] += 1
                d["teams"][_canon(r[3])] += 1
                bl = _balls(r[5])
                if not bl:
                    continue
                d["inns"] += 1
                d["balls"] += bl; d["runs"] += int(r[7])
                d["wkts"] += int(r[8]); d["dots"] += int(r[9])
                w, runs = int(r[8]), int(r[7])
                if (w, -runs) > (d["bestW"], -d["bestR"]):
                    d["bestW"], d["bestR"] = w, runs

    def finish(d, kind):
        name = d["names"].most_common(1)[0][0]
        team = d["teams"].most_common(1)[0][0]
        row = dict(name=name, team=team, inns=d["inns"],
                   ours=team == US, g5=_group_of(team) == OUR_GROUP)
        if kind == "bat":
            row.update(runs=d["runs"], balls=d["balls"], best=d["best"],
                       fours=d["fours"], sixes=d["sixes"],
                       sr=round(d["runs"] / d["balls"] * 100, 1) if d["balls"] else None,
                       avg=round(d["runs"] / d["outs"], 1) if d["outs"] else None)
        else:
            row.update(wkts=d["wkts"], runs=d["runs"], balls=d["balls"],
                       overs=round(d["balls"] / 6, 1),
                       econ=round(d["runs"] / (d["balls"] / 6), 2) if d["balls"] else None,
                       dotPct=round(d["dots"] / d["balls"] * 100, 1) if d["balls"] else None,
                       best="%d-%d" % (d["bestW"], d["bestR"]) if d["bestW"] >= 0 else "-")
        return row

    batters = [finish(d, "bat") for d in bat.values()]
    bowlers = [finish(d, "bowl") for d in bowl.values()]

    boards = dict(
        runs=sorted(batters, key=lambda x: (-x["runs"], -(x["sr"] or 0)))[:10],
        wickets=sorted([b for b in bowlers if b["wkts"]],
                       key=lambda x: (-x["wkts"], x["econ"] if x["econ"] is not None else 99))[:10],
        strikeRate=sorted([b for b in batters if b["balls"] >= MIN_SR_BALLS],
                          key=lambda x: -(x["sr"] or 0))[:10],
        economy=sorted([b for b in bowlers if b["balls"] >= MIN_ECON_BALLS],
                       key=lambda x: (x["econ"] if x["econ"] is not None else 99))[:10],
        sixes=sorted([b for b in batters if b["sixes"]],
                     key=lambda x: (-x["sixes"], -x["runs"]))[:5],
    )
    return dict(
        matches=len(n_matches),
        players=len(bat),
        boards=boards,
        minimums=dict(strikeRate="%d balls faced" % MIN_SR_BALLS,
                      economy="%d balls bowled" % MIN_ECON_BALLS),
        note=("Computed from every completed match's full scorecard - the same "
              "harvest as the results and the points table, so the three always "
              "agree. Volume boards (runs, wickets) have no minimum; rate boards "
              "carry one so a six-ball cameo cannot top them. Early-season "
              "numbers rest on one or two games - the innings column says so."),
    )


if __name__ == "__main__":
    d = build_leaders2026()
    if not d:
        print("no results file")
    else:
        print("%d matches, %d players with a bat row" % (d["matches"], d["players"]))
        for board, rows in d["boards"].items():
            print("\n%s:" % board.upper())
            for r in rows[:5]:
                tag = " <US>" if r["ours"] else (" <G5>" if r["g5"] else "")
                if "wkts" in r:
                    print("  %-24s %-22s %dw, econ %s, best %s (%d inns)%s" % (
                        r["name"][:24], r["team"][:22], r["wkts"], r["econ"], r["best"], r["inns"], tag))
                else:
                    print("  %-24s %-22s %dr @ SR %s, HS %d (%d inns)%s" % (
                        r["name"][:24], r["team"][:22], r["runs"], r["sr"], r["best"], r["inns"], tag))
