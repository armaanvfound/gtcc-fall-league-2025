"""Phase-by-phase analysis from the 40-match ball-by-ball sample in ../phase-data/.

Each phase-data/<matchid>.json holds per-over [over, runs, wickets, bowler_type]
for both innings, collected from CricHeroes commentary and validated against the
known match totals.
"""
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE_DIR = HERE.parent / "phase-data"

PP, MID, DEATH = "pp", "mid", "death"


def phase_of(over):
    if over <= 5:
        return PP
    if over <= 10:
        return MID
    return DEATH


def load_matches():
    out = []
    for f in sorted(PHASE_DIR.glob("[0-9]*.json")):
        out.append(json.loads(f.read_text()))
    return out


def innings_rows(matches):
    """One row per innings that ran the full 15 overs.

    Innings cut short (all out, or a chase finished early) have no comparable
    death phase, so they are excluded from phase averages.
    """
    rows = []
    for d in matches:
        if d.get("quota", 15) != 15:
            continue
        for inn in d["innings"]:
            overs = inn["overs"]
            if len(overs) < 15:
                continue
            acc = {PP: [0, 0], MID: [0, 0], DEATH: [0, 0]}
            for o in overs:
                p = acc[phase_of(o[0])]
                p[0] += o[1]
                p[1] += o[2]
            rows.append({
                "mid": d["mid"], "round": d["round"],
                "team": inn["batting"], "opp": inn["bowling"],
                "bat_order": inn["bat_order"], "won": inn["won"],
                "total": sum(o[1] for o in overs),
                "wkts": sum(o[2] for o in overs),
                "pp_r": acc[PP][0], "pp_w": acc[PP][1],
                "mid_r": acc[MID][0], "mid_w": acc[MID][1],
                "death_r": acc[DEATH][0], "death_w": acc[DEATH][1],
            })
    return rows


def _avg(rows, key):
    return round(sum(r[key] for r in rows) / len(rows), 1) if rows else 0


def _summary(rows):
    return {
        "n": len(rows),
        "pp": _avg(rows, "pp_r"), "ppw": _avg(rows, "pp_w"),
        "mid": _avg(rows, "mid_r"), "midw": _avg(rows, "mid_w"),
        "death": _avg(rows, "death_r"), "deathw": _avg(rows, "death_w"),
        "total": _avg(rows, "total"),
    }


def classify_type(t):
    if not t:
        return None
    s = t.lower()
    if 'orthodox' in s or 'break' in s or 'spin' in s or 'googly' in s or 'chinaman' in s:
        return 'spin'
    if 'fast' in s or 'medium' in s:
        return 'pace'
    return None


def bowl_types(matches):
    """Pace vs spin, from the ~26% of overs whose bowler type was legible.

    Pace has a real sample; spin does not - the league is overwhelmingly
    medium/fast. Both facts are reported as such.
    """
    agg = defaultdict(lambda: dict(overs=0, runs=0, wkts=0))
    typed = total = 0
    for d in matches:
        for inn in d["innings"]:
            for o in inn["overs"]:
                total += 1
                cls = classify_type(o[3])
                if o[3]:
                    typed += 1
                if not cls:
                    continue
                for key in (cls, cls + ":" + phase_of(o[0])):
                    a = agg[key]
                    a["overs"] += 1
                    a["runs"] += o[1]
                    a["wkts"] += o[2]

    def econ(k):
        a = agg.get(k)
        if not a or not a["overs"]:
            return None
        return dict(n=a["overs"], econ=round(a["runs"] / a["overs"], 2),
                    wpo=round(a["wkts"] / a["overs"], 2))

    return {
        "typedOvers": typed, "totalOvers": total,
        "pace": econ("pace"), "spin": econ("spin"),
        "pacePhases": {p: econ("pace:" + p) for p in (PP, MID, DEATH)},
    }


def team_phase_table(rows):
    """Per-team phase splits, batting and bowling, for the scouting cards."""
    bat = defaultdict(list)
    bowl = defaultdict(list)
    for r in rows:
        bat[r["team"]].append(r)
        bowl[r["opp"]].append(r)

    out = {}
    for team in set(list(bat) + list(bowl)):
        b, d = bat.get(team, []), bowl.get(team, [])
        out[team] = {
            "bat": _summary(b) if b else None,
            "bowl": _summary(d) if d else None,
        }
    return out


def build_phases():
    matches = load_matches()
    rows = innings_rows(matches)

    won = [r for r in rows if r["won"]]
    lost = [r for r in rows if not r["won"]]
    bat1 = [r for r in rows if r["bat_order"] == 1]
    bat2 = [r for r in rows if r["bat_order"] == 2]

    # Which phase separates winners from losers by the most runs?
    gaps = {
        "pp": round(_avg(won, "pp_r") - _avg(lost, "pp_r"), 1),
        "mid": round(_avg(won, "mid_r") - _avg(lost, "mid_r"), 1),
        "death": round(_avg(won, "death_r") - _avg(lost, "death_r"), 1),
    }
    decisive = max(gaps, key=lambda k: gaps[k])

    # Milestone: what score at the end of each phase preceded a 120+ total?
    reached = [r for r in bat1 if r["total"] >= 120]
    missed = [r for r in bat1 if r["total"] < 120]

    weather = []
    wf = PHASE_DIR / "_weather_by_date.json"
    if wf.exists():
        weather = json.loads(wf.read_text())

    return {
        "sample": {"matches": len(matches), "innings": len(rows)},
        "all": _summary(rows),
        "won": _summary(won),
        "lost": _summary(lost),
        "bat1": _summary(bat1),
        "bat2": _summary(bat2),
        "gaps": gaps,
        "decisive": decisive,
        "milestone": {
            "reached": _summary(reached),
            "missed": _summary(missed),
        },
        "teams": team_phase_table(rows),
        "bowlTypes": bowl_types(matches),
        "weather": weather,
    }


if __name__ == "__main__":
    p = build_phases()
    print(json.dumps({k: v for k, v in p.items() if k != "teams"}, indent=1))
    print(f"\n{len(p['teams'])} teams have phase data")
