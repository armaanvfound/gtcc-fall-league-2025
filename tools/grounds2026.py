"""How each ground is playing this season, against how it played last season.

Per ground: 2026 matches, average first- and second-innings totals, the
bat-first record and all-out count - beside the same numbers from 2025, so
"this ground is playing lower this year" is a read anyone can make from the
page instead of a thing someone has to remember.

Ground names need normalising before they can be compared. The 2026 harvest
says "GTCC Ajax Cricket Ground" where the 2025 data says the same; the schedule
sheet says "GTCC Ajax Ground"; and 2025 also contains "Stom Street Park" - a
CricHeroes typo venue holding five real Stone Street matches, which are merged
into Stone Street's 2025 numbers here (weighted by matches, so the merge is
exact, not cosmetic).

Second-innings averages carry the same structural caveat as team chasing
averages: a successful chase stops at the target, so avg2 reads low wherever
chasing sides win often.
"""
import re
from pathlib import Path

from results2026 import build_results2026

ROOT = Path(__file__).resolve().parent.parent

# normalised-key aliases for known misspellings
GROUND_ALIASES = {"stomstreet": "stonestreet"}


def ground_key(name):
    k = re.sub(r"cricket|ground|park|memorial|-|,|oshawa|whitby", "",
               str(name or "").lower())
    k = re.sub(r"[^a-z]", "", k)
    return GROUND_ALIASES.get(k, k)


def build_grounds2026(payload_league=None):
    res = build_results2026()
    if not res or not res["matches"]:
        return None

    g26 = {}
    for m in res["matches"]:
        k = ground_key(m["ground"])
        g = g26.setdefault(k, dict(name=m["ground"], n=0, s1=[], s2=[],
                                   bfw=0, allout=0))
        g["n"] += 1
        g["s1"].append(m["first"]["runs"])
        g["s2"].append(m["second"]["runs"])
        g["bfw"] += 1 if m["batFirstWon"] else 0
        g["allout"] += (1 if m["first"].get("allOut") else 0) + \
                       (1 if m["second"].get("allOut") else 0)

    # 2025, merged by the same key (this is where Stom Street folds into Stone
    # Street: recombine the weighted sums, never average the averages)
    g25 = {}
    for v in (payload_league or {}).get("venues") or []:
        k = ground_key(v["venue"])
        d = g25.setdefault(k, dict(n=0, sum1=0, sum2=0, bfw=0, allout=0))
        d["n"] += v["n"]
        d["sum1"] += v["avg1"] * v["n"]
        d["sum2"] += v["avg2"] * v["n"]
        d["bfw"] += round(v["pct"] / 100 * v["n"])
        d["allout"] += v.get("allout", 0)

    out = []
    for k, g in sorted(g26.items(), key=lambda kv: -kv[1]["n"]):
        row = dict(
            ground=g["name"], n=g["n"],
            avg1=round(sum(g["s1"]) / g["n"]),
            avg2=round(sum(g["s2"]) / g["n"]),
            batFirstWins=g["bfw"], allOuts=g["allout"])
        p = g25.get(k)
        if p:
            row["y2025"] = dict(
                n=p["n"], avg1=round(p["sum1"] / p["n"]),
                avg2=round(p["sum2"] / p["n"]),
                batFirstPct=round(p["bfw"] / p["n"] * 100),
                allOuts=p["allout"])
        out.append(row)

    return dict(
        grounds=out,
        note=("Per ground, this season beside last. avg2 reads low by "
              "construction wherever chasing sides win - a successful chase "
              "stops at the target. 2025's 'Stom Street Park' typo venue is "
              "merged into Stone Street, weighted by matches."),
    )


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import build_payload
    d = build_grounds2026(build_payload()["league"])
    for g in d["grounds"]:
        p = g.get("y2025")
        print("%-28s 2026: n=%d 1st %d / 2nd %d, bat-first %d/%d, allout %d" % (
            g["ground"][:28], g["n"], g["avg1"], g["avg2"], g["batFirstWins"],
            g["n"], g["allOuts"]))
        if p:
            print("%-28s 2025: n=%d 1st %d / 2nd %d, bat-first %d%%, allout %d" % (
                "", p["n"], p["avg1"], p["avg2"], p["batFirstPct"], p["allOuts"]))
