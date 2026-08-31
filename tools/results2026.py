"""2026 league results as they accumulate - the season's live intel.

Reads league-raw/results-2026.tsv, harvested from CricHeroes (tournament id
2167460) with the snippet in tools/collector.js - see the README in league-raw.
Re-run the harvest after each weekend and this whole picture updates: the
dashboard section, and the running numbers the assistant quotes.

Why this matters more every week: the 2025 numbers are a different season with
different squads. Every 2026 result replaces inference with observation - what
a real first-innings score looks like now, whether the bat-first edge held, and
above all how OUR five group opponents are actually going. Rows here about a
G5 side are scouting gold; everything else calibrates the environment.

Format, tab-separated (M = match meta, I = innings, B/W = full cards):
  M  mid date ground toss winner margin matchType
  I  mid inn team runs wkts overs extras
  B  mid inn battingTeam player runs balls 4s 6s SR hand howOut playerId
  W  mid inn bowlingTeam player overs maidens runs wkts dots 4s 6s wides noballs econ playerId
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "league-raw" / "results-2026.tsv"

US = "Royal Challenger Blaster"

# Group composition, from the official schedule (tools/schedule.py reads the
# same sheet). Used to tag every result with the group it belongs to.
GROUPS = {
    "Group 1": ["Desi Cric Champs", "Feral", "Durham Spartans Cricket Club",
                "Maple Eagles", "Scarborough Strikers", "Sunrisers Harmony"],
    "Group 2": ["ThunderStrikers", "Toronto Sharks", "DesiBoyz CC",
                "Super Challengers", "YRICA team", "Downtown Hunterz"],
    "Group 3": ["Pappampati", "Golden City", "Whitby Thunderbolts",
                "Red wings", "Maratha Warriors", "Gully Boys"],
    "Group 4": ["Royal Punjab", "NorthStars", "Deccan Avengers",
                "Panjab XI", "Nizam Royal Knights", "Royals"],
    "Group 5": ["Durham United", US, "Invincible Trailblazers",
                "South Warriors", "Lisa Challengers", "United Punjab"],
    "Group 6": ["Mavericks", "Trailblazers", "Durham Strikers",
                "Fighters", "Maple Marvels", "Garuda Reapers"],
}

# CricHeroes team names -> schedule names, where they differ.
ALIASES = {
    "Durham Strikers - T15": "Durham Strikers",
    "YRICA": "YRICA team",
    "Royal challengers blaster": US,
}


def _canon(name):
    name = (name or "").strip()
    return ALIASES.get(name, name)


def _group_of(team):
    for g, members in GROUPS.items():
        if team in members:
            return g
    return None


def build_results2026():
    if not SRC.exists():
        return None
    matches = {}
    with SRC.open(encoding="utf-8") as fh:
        for r in csv.reader(fh, delimiter="\t"):
            if not r:
                continue
            mid = r[1]
            m = matches.setdefault(mid, {"mid": mid, "innings": [], "bat": [], "bowl": []})
            if r[0] == "M":
                m.update(date=r[2], ground=r[3], toss=r[4],
                         winner=_canon(r[5]), margin=r[6])
            elif r[0] == "I":
                m["innings"].append(dict(
                    order=int(r[2]), team=_canon(r[3]), runs=int(r[4]),
                    wkts=int(r[5]), overs=r[6], extras=int(r[7])))
            elif r[0] == "B":
                m["bat"].append(dict(team=_canon(r[3]), name=r[4], runs=int(r[5]),
                                     balls=int(r[6]), hand=r[10], howOut=r[11]))
            elif r[0] == "W":
                m["bowl"].append(dict(team=_canon(r[3]), name=r[4], overs=r[5],
                                      runs=int(r[7]), wkts=int(r[8]), dots=int(r[9])))

    out = []
    for m in matches.values():
        if len(m["innings"]) != 2:
            continue
        first = next(i for i in m["innings"] if i["order"] == 1)
        second = next(i for i in m["innings"] if i["order"] == 2)
        grp = _group_of(first["team"]) or _group_of(second["team"])
        batFirstWon = m.get("winner") == first["team"]
        # the standouts, for the one-line story of each match
        top_bat = max(m["bat"], key=lambda b: b["runs"], default=None)
        top_bowl = min(
            [w for w in m["bowl"] if w["wkts"] > 0] or m["bowl"],
            key=lambda w: (-w["wkts"], w["runs"]), default=None)
        out.append(dict(
            mid=m["mid"], date=m.get("date"), ground=m.get("ground"),
            group=grp, toss=m.get("toss"), winner=m.get("winner"),
            margin=m.get("margin"), batFirstWon=batFirstWon,
            first=dict(team=first["team"], runs=first["runs"],
                       wkts=first["wkts"], overs=first["overs"]),
            second=dict(team=second["team"], runs=second["runs"],
                        wkts=second["wkts"], overs=second["overs"]),
            topBat=(dict(name=top_bat["name"], team=top_bat["team"],
                         runs=top_bat["runs"], balls=top_bat["balls"])
                    if top_bat else None),
            topBowl=(dict(name=top_bowl["name"], team=top_bowl["team"],
                          wkts=top_bowl["wkts"], runs=top_bowl["runs"],
                          overs=top_bowl["overs"]) if top_bowl else None),
            involvesOurGroup=grp == "Group 5",
        ))
    out.sort(key=lambda x: (x["date"] or "", x["mid"]))

    n = len(out)
    firsts = [r["first"]["runs"] for r in out]
    bf = sum(1 for r in out if r["batFirstWon"])
    # per-team 2026 form, most useful for our five opponents
    form = {}
    for r in out:
        for side, res in ((r["first"]["team"], r["winner"] == r["first"]["team"]),
                          (r["second"]["team"], r["winner"] == r["second"]["team"])):
            f = form.setdefault(side, {"p": 0, "w": 0})
            f["p"] += 1
            f["w"] += 1 if res else 0

    return dict(
        matches=out,
        totals=dict(
            played=n,
            avgFirstInnings=round(sum(firsts) / n, 1) if n else None,
            batFirstWins=bf,
            batFirstPct=round(bf / n * 100) if n else None,
            highestFirst=max(firsts) if firsts else None,
            lowestFirst=min(firsts) if firsts else None,
        ),
        form2026=form,
        g5=[r for r in out if r["involvesOurGroup"]],
        note=("2026 league results, harvested from CricHeroes after each round. "
              "Small samples early on - say how many matches a number rests on."),
    )


if __name__ == "__main__":
    d = build_results2026()
    if not d:
        print("no results file")
    else:
        t = d["totals"]
        print("%d played | avg 1st inns %s | bat-first %d/%d" %
              (t["played"], t["avgFirstInnings"], t["batFirstWins"], t["played"]))
        for r in d["matches"]:
            print("  %s %-8s %s %d/%d v %s %d/%d -> %s by %s" % (
                r["date"], (r["group"] or "?"), r["first"]["team"], r["first"]["runs"],
                r["first"]["wkts"], r["second"]["team"], r["second"]["runs"],
                r["second"]["wkts"], r["winner"], r["margin"]))
