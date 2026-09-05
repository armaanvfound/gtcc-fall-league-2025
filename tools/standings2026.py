"""Group standings for the 2026 league, computed from our own results file.

CricHeroes has a points table, but it renders client-side behind Cloudflare, so
it cannot be read on a sync. It also does not need to be: every completed
scorecard is already in league-raw/results-2026.tsv, and a points table is pure
arithmetic over results. Computing it ourselves means the standings update on
the same sync as everything else and can never disagree with the results shown
beside them.

Rules, from the official format (2 points a win, 1 a tie/no-result; the top two
of each group plus the two best third-placed sides advance, tiebreak NRR):

Net run rate uses the all-out rule - a side bowled out counts as having batted
its full quota of overs. That is the rule that moved our own NRR from a wrong
+0.84 to the +1.39 CricHeroes shows, so the standings apply it everywhere.
"""
from pathlib import Path

from results2026 import GROUPS, build_results2026, _canon  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
QUOTA = 15   # overs per side, league phase


def _overs_to_float(txt):
    s = str(txt)
    if "." not in s:
        return float(s)
    o, b = s.split(".")
    return int(o) + int(b) / 6.0


def _nrr_overs(inn):
    actual = _overs_to_float(inn["overs"])
    return max(actual, float(QUOTA)) if inn.get("allOut") else actual


def build_standings2026():
    res = build_results2026()
    if not res or not res["matches"]:
        return None

    teams = {}

    def row(team, group):
        return teams.setdefault(team, dict(
            team=team, group=group, played=0, won=0, lost=0, tied=0, points=0,
            runsFor=0.0, oversFor=0.0, runsAgainst=0.0, oversAgainst=0.0))

    for m in res["matches"]:
        f, s = m["first"], m["second"]
        grp = m["group"]
        a, b = row(f["team"], grp), row(s["team"], grp)
        for me, them, mine in ((a, s, f), (b, f, s)):
            me["played"] += 1
            me["runsFor"] += mine["runs"]
            me["oversFor"] += _nrr_overs(mine)
            me["runsAgainst"] += them["runs"]
            me["oversAgainst"] += _nrr_overs(them)
        if m["winner"] == f["team"]:
            a["won"] += 1; b["lost"] += 1; a["points"] += 2
        elif m["winner"] == s["team"]:
            b["won"] += 1; a["lost"] += 1; b["points"] += 2
        else:
            a["tied"] += 1; b["tied"] += 1; a["points"] += 1; b["points"] += 1

    for t in teams.values():
        t["nrr"] = (round(t["runsFor"] / t["oversFor"]
                          - t["runsAgainst"] / t["oversAgainst"], 2)
                    if t["oversFor"] and t["oversAgainst"] else None)
        for k in ("runsFor", "oversFor", "runsAgainst", "oversAgainst"):
            t[k] = round(t[k], 2)

    groups = {}
    for gname, members in GROUPS.items():
        rows = []
        for name in members:
            t = teams.get(name)
            rows.append(t if t else dict(
                team=name, group=gname, played=0, won=0, lost=0, tied=0,
                points=0, nrr=None, runsFor=0, oversFor=0,
                runsAgainst=0, oversAgainst=0))
        rows.sort(key=lambda t: (-t["points"],
                                 -(t["nrr"] if t["nrr"] is not None else -99),
                                 t["team"]))
        groups[gname] = rows

    return dict(
        groups=groups,
        source=dict(
            name="GTCC Fall League 2026 on CricHeroes",
            url="https://cricheroes.com/tournament/2167460/gtcc-fall-league-2026",
            share="https://chshare.link/tournament/54auYA",
        ),
        note=("Computed from the harvested scorecards - 2 points a win, 1 a tie; "
              "NRR applies the all-out rule (a side bowled out counts as its full "
              "%d overs). Top two per group advance plus the two best third-placed "
              "sides, so NRR is the tiebreak that decides seasons." % QUOTA),
    )


if __name__ == "__main__":
    d = build_standings2026()
    if not d:
        print("no results yet")
    else:
        for g, rows in d["groups"].items():
            if not any(r["played"] for r in rows):
                continue
            print(g)
            for r in rows:
                print("  %-28s P%d W%d L%d T%d  %2dpts  NRR %s" % (
                    r["team"][:28], r["played"], r["won"], r["lost"], r["tied"],
                    r["points"], ("%+.2f" % r["nrr"]) if r["nrr"] is not None else "-"))
