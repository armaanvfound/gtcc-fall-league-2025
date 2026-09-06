"""What we need: the Group 5 qualification picture, computed each sync.

Top two of each group advance, plus the two best third-placed sides; NRR is
the tiebreak. From about round three the question every teammate asks is
"what do we need on Saturday?" - so this answers it from the standings and the
remaining fixtures, conservatively:

  - each side's points, games left and the MOST points it can still reach;
  - the wins from our remaining games that GUARANTEE a top-two finish whatever
    anyone else does (our final points strictly above the second-highest
    ceiling among the others);
  - and, short of that, what it comes down to.

"Guarantee" is deliberately the strict reading. It never says we are through
on the strength of results that have not happened; it says the least that
makes the arithmetic certain, and names the tiebreak otherwise.
"""
from pathlib import Path

from results2026 import GROUPS
from standings2026 import build_standings2026
from schedule import build_schedule

ROOT = Path(__file__).resolve().parent.parent
US = "Royal Challenger Blaster"
OUR_GROUP = "Group 5"
WIN = 2


def _canon_sched(name):
    # schedule-sheet spellings that differ from the results canon
    return {"Feral": "FERAL XI"}.get(name, name)


def build_qualify2026():
    st = build_standings2026()
    sch = build_schedule()
    if not st or not sch:
        return None
    rows = {r["team"]: r for r in st["groups"][OUR_GROUP]}

    # remaining fixtures = scheduled group games between two G5 sides that have
    # not produced a result yet (matched on the unordered team pair)
    played_pairs = set()
    from results2026 import build_results2026
    res = build_results2026() or {"matches": []}
    for m in res["matches"]:
        played_pairs.add(frozenset((m["first"]["team"], m["second"]["team"])))
    members = set(GROUPS[OUR_GROUP])
    remaining = []
    for f in sch["groupMatches"]:
        a, b = _canon_sched(f["t1"]), _canon_sched(f["t2"])
        if a in members and b in members and frozenset((a, b)) not in played_pairs:
            remaining.append(dict(date=f["date"], disp=f["disp"], t1=a, t2=b,
                                  ground=f.get("groundShort") or f.get("ground")))
    remaining.sort(key=lambda x: x["date"])

    table = []
    for name in GROUPS[OUR_GROUP]:
        r = rows[name]
        left = [x for x in remaining if name in (x["t1"], x["t2"])]
        table.append(dict(
            team=name, played=r["played"], won=r["won"], points=r["points"],
            nrr=r["nrr"], left=len(left), maxPoints=r["points"] + WIN * len(left),
            next=[(x["t2"] if x["t1"] == name else x["t1"]) for x in left]))
    table.sort(key=lambda t: (-t["points"], -(t["nrr"] if t["nrr"] is not None else -99)))

    us = next(t for t in table if t["team"] == US)
    others = [t for t in table if t["team"] != US]
    ceilings = sorted((t["maxPoints"] for t in others), reverse=True)
    second_ceiling = ceilings[1] if len(ceilings) > 1 else 0
    # wins from our remaining games that put us strictly above the second-highest
    # ceiling among the others -> top two is certain
    need = None
    for w in range(0, us["left"] + 1):
        if us["points"] + WIN * w > second_ceiling:
            need = w
            break
    guaranteed = need == 0

    if guaranteed:
        read = ("Top two is already certain: our %d points are more than any side bar one "
                "can still reach." % us["points"])
    elif need is not None:
        read = ("Win <b>%d of our remaining %d</b> and top two is guaranteed whatever anyone else "
                "does. Fewer than that and it comes down to other results and net run rate - "
                "the two best third-placed sides also go through, so a strong NRR is the "
                "insurance." % (need, us["left"]))
    else:
        read = ("Top two cannot be guaranteed by our own results alone - it depends on others' "
                "results and net run rate. The two best third-placed sides also advance.")

    return dict(
        table=table, remaining=remaining, us=us,
        needWins=need, guaranteed=guaranteed, secondCeiling=second_ceiling,
        read=read,
        rules="Top two per group advance, plus the two best third-placed sides; NRR is the tiebreak.",
    )


if __name__ == "__main__":
    d = build_qualify2026()
    if not d:
        print("no data")
    else:
        print(d["read"].replace("<b>", "").replace("</b>", ""))
        for t in d["table"]:
            print("  %-26s P%d %2dpts  left %d  max %2d  next: %s" % (
                t["team"][:26], t["played"], t["points"], t["left"], t["maxPoints"],
                ", ".join(n[:14] for n in t["next"])))
        print("remaining G5 fixtures:", len(d["remaining"]))
