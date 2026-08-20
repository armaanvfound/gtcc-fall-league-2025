"""Our own matches: per-match record, phase and dot-ball splits, player careers.

Reads every ../our-matches/<mid>.json. Each file is one match we played, in the
shape described in that directory's README, and was transcribed ball by ball
from the CricHeroes commentary tab and reconciled against the scorecard: for all
six innings recorded so far the parsed runs, wickets, legal deliveries and
per-bowler figures match the published card exactly.

Two things this module refuses to do, because both would flatter us:

Only 15-over matches are compared against the league. tools/phases.py builds its
par from 15-over league cricket; a 12-over innings has no fifth-over powerplay
and an 8-over hit-out has no death at all, so laying either against that par
would invent a result. Non-15-over matches still appear in the per-match log and
still feed player careers, where balls faced and runs conceded mean the same
thing whatever the quota.

Dot balls are counted the strict way: a legal delivery off which no runs at all
were scored. CricHeroes counts a bye or leg bye as a dot for the batter; we do
not, because a run was scored. That is the only place our count and theirs can
differ, and it is one ball in six innings so far.
"""
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIR = HERE.parent / "our-matches"
PHASES = ("pp", "mid", "death")
# index into a phase array
BALLS, DOTS, RUNS, WKTS = 0, 1, 2, 3


def load():
    out = []
    for f in sorted(DIR.glob("[0-9]*.json")):
        out.append(json.loads(f.read_text()))
    out.sort(key=lambda m: m["date"], reverse=True)
    return out


def _overs_to_float(txt):
    """'13.4' -> 13.6667. Cricket notation: the decimal is balls, not tenths."""
    s = str(txt)
    if "." not in s:
        return float(s)
    o, b = s.split(".")
    return int(o) + int(b) / 6.0


def _pct(n, d):
    return round(n / d * 100, 1) if d else None


def _rate(runs, overs):
    return round(runs / overs, 2) if overs else None


def phase_labels(m):
    """Human labels for this match's phase boundaries, e.g. '1-5' / '6-10'."""
    a, b = m["phaseBounds"]
    last = int(float(m["quota"]))
    return {"pp": "1-%d" % a, "mid": "%d-%d" % (a + 1, b), "death": "%d-%d" % (b + 1, last)}


def match_rows(matches):
    """One row per match for the log, with both innings and the match net run rate."""
    rows = []
    for m in matches:
        us, them = m["ourInnings"], m["theirInnings"]
        ourOv = _overs_to_float(us["oversText"])
        theirOv = _overs_to_float(them["oversText"])
        rows.append(dict(
            mid=m["mid"], date=m["date"], opp=m["opp"], venue=m["venue"],
            competition=m["competition"], isLeague=m["isLeague"], quota=m["quota"],
            quotaNote=m.get("quotaNote"), toss=m["toss"], result=m["result"],
            margin=m["margin"], url=m.get("url"), labels=phase_labels(m),
            us=dict(order=us["order"], runs=us["runs"], wkts=us["wkts"],
                    overs=us["oversText"], balls=us["balls"], rpo=_rate(us["runs"], ourOv),
                    dots=sum(us["phases"][p][DOTS] for p in PHASES),
                    dotPct=_pct(sum(us["phases"][p][DOTS] for p in PHASES), us["balls"]),
                    extras=us["wideRuns"] + us["noBalls"], phases=us["phases"]),
            them=dict(order=them["order"], runs=them["runs"], wkts=them["wkts"],
                      overs=them["oversText"], balls=them["balls"],
                      rpo=_rate(them["runs"], theirOv),
                      dots=sum(them["phases"][p][DOTS] for p in PHASES),
                      dotPct=_pct(sum(them["phases"][p][DOTS] for p in PHASES), them["balls"]),
                      extras=them["wideRuns"] + them["noBalls"], phases=them["phases"]),
            nrr=round(us["runs"] / ourOv - them["runs"] / theirOv, 2),
        ))
    return rows


def _blank():
    return {p: [0, 0, 0, 0] for p in PHASES}


def _add(acc, ph):
    for p in PHASES:
        for i in range(4):
            acc[p][i] += ph[p][i]


def phase_totals(matches, only15=False):
    """Aggregate phase splits for our batting and our bowling."""
    bat, bowl = _blank(), _blank()
    n = 0
    for m in matches:
        if only15 and int(float(m["quota"])) != 15:
            continue
        n += 1
        _add(bat, m["ourInnings"]["phases"])
        _add(bowl, m["theirInnings"]["phases"])

    def pack(acc):
        return {p: dict(balls=acc[p][BALLS], dots=acc[p][DOTS], runs=acc[p][RUNS],
                        wkts=acc[p][WKTS], dotPct=_pct(acc[p][DOTS], acc[p][BALLS]),
                        rpo=round(acc[p][RUNS] / (acc[p][BALLS] / 6), 2) if acc[p][BALLS] else None)
                for p in PHASES}

    tb = sum(bat[p][BALLS] for p in PHASES)
    tw = sum(bowl[p][BALLS] for p in PHASES)
    return dict(
        matches=n,
        bat=pack(bat), bowl=pack(bowl),
        batOverall=dict(balls=tb, dots=sum(bat[p][DOTS] for p in PHASES),
                        dotPct=_pct(sum(bat[p][DOTS] for p in PHASES), tb)),
        bowlOverall=dict(balls=tw, dots=sum(bowl[p][DOTS] for p in PHASES),
                         dotPct=_pct(sum(bowl[p][DOTS] for p in PHASES), tw)),
    )


def bowler_table(matches):
    """Per-bowler career, split by phase, with dot percentage in each."""
    agg = {}
    for m in matches:
        for name, d in m["theirInnings"]["ourBowling"].items():
            a = agg.setdefault(name, dict(name=name, matches=0, overs=0.0, runs=0,
                                          wkts=0, ph=_blank()))
            a["matches"] += 1
            a["overs"] += float(d["o"])
            a["runs"] += d["r"]
            a["wkts"] += d["w"]
            _add(a["ph"], d["ph"])
    out = []
    for a in agg.values():
        balls = sum(a["ph"][p][BALLS] for p in PHASES)
        dots = sum(a["ph"][p][DOTS] for p in PHASES)
        out.append(dict(
            name=a["name"], matches=a["matches"], overs=round(a["overs"], 1),
            runs=a["runs"], wkts=a["wkts"],
            econ=_rate(a["runs"], a["overs"]),
            avg=round(a["runs"] / a["wkts"], 1) if a["wkts"] else None,
            sr=round(balls / a["wkts"], 1) if a["wkts"] else None,
            balls=balls, dots=dots, dotPct=_pct(dots, balls),
            ph={p: dict(balls=a["ph"][p][BALLS], dots=a["ph"][p][DOTS],
                        runs=a["ph"][p][RUNS], wkts=a["ph"][p][WKTS],
                        dotPct=_pct(a["ph"][p][DOTS], a["ph"][p][BALLS]),
                        econ=round(a["ph"][p][RUNS] / (a["ph"][p][BALLS] / 6), 2)
                        if a["ph"][p][BALLS] else None)
                for p in PHASES},
        ))
    out.sort(key=lambda x: (-x["wkts"], x["econ"] if x["econ"] is not None else 99))
    return out


def batter_table(matches):
    """Per-batter career. Average is runs per dismissal; not-outs never count as one."""
    agg = {}
    for m in matches:
        for name, r, b, f4, f6, out_ in m["ourInnings"]["batting"]:
            a = agg.setdefault(name, dict(name=name, inns=0, runs=0, balls=0, outs=0,
                                          f4=0, f6=0, best=0, notOuts=0))
            a["inns"] += 1
            a["runs"] += r
            a["balls"] += b
            a["f4"] += f4
            a["f6"] += f6
            a["outs"] += 1 if out_ else 0
            a["notOuts"] += 0 if out_ else 1
            if r > a["best"]:
                a["best"] = r
    rows = []
    for a in agg.values():
        rows.append(dict(
            name=a["name"], inns=a["inns"], runs=a["runs"], balls=a["balls"],
            outs=a["outs"], notOuts=a["notOuts"], f4=a["f4"], f6=a["f6"], best=a["best"],
            avg=round(a["runs"] / a["outs"], 1) if a["outs"] else None,
            sr=round(a["runs"] / a["balls"] * 100, 1) if a["balls"] else None,
            bdryPct=_pct(a["f4"] * 4 + a["f6"] * 6, a["runs"]) if a["runs"] else None,
        ))
    rows.sort(key=lambda x: -x["runs"])
    return rows


def record(matches):
    w = sum(1 for m in matches if m["result"] == "won")
    l = sum(1 for m in matches if m["result"] == "lost")
    t = sum(1 for m in matches if m["result"] == "tied")
    rf = ro = ra = oo = 0.0
    for m in matches:
        rf += m["ourInnings"]["runs"]
        ro += _overs_to_float(m["ourInnings"]["oversText"])
        ra += m["theirInnings"]["runs"]
        oo += _overs_to_float(m["theirInnings"]["oversText"])
    opps = sorted({m["opp"] for m in matches})
    return dict(played=len(matches), won=w, lost=l, tied=t,
                opponents=opps, oppCount=len(opps),
                leagueCount=sum(1 for m in matches if m["isLeague"]),
                runsFor=int(rf), oversFor=round(ro, 2),
                runsAgainst=int(ra), oversAgainst=round(oo, 2),
                nrr=round(rf / ro - ra / oo, 2) if ro and oo else None)


def build_ours():
    matches = load()
    if not matches:
        return None
    m15 = [m for m in matches if int(float(m["quota"])) == 15]
    return dict(
        record=record(matches),
        matches=match_rows(matches),
        all=phase_totals(matches),
        fifteen=phase_totals(matches, only15=True),
        fifteenCount=len(m15),
        bowlers=bowler_table(matches),
        batters=batter_table(matches),
    )


if __name__ == "__main__":
    d = build_ours()
    r = d["record"]
    print("played %d: %dW %dL %dT vs %s | NRR %+.2f" % (
        r["played"], r["won"], r["lost"], r["tied"], ", ".join(r["opponents"]), r["nrr"]))
    for m in d["matches"]:
        print("  %s %2s ov vs %-10s  us %3d/%-2d (%s)  them %3d/%-2d (%s)  %-5s NRR %+.2f" % (
            m["date"], m["quota"], m["opp"], m["us"]["runs"], m["us"]["wkts"], m["us"]["overs"],
            m["them"]["runs"], m["them"]["wkts"], m["them"]["overs"], m["result"], m["nrr"]))
    print("\ndot%% all matches  bat %.1f  bowl %.1f" % (
        d["all"]["batOverall"]["dotPct"], d["all"]["bowlOverall"]["dotPct"]))
    for p in PHASES:
        print("  %-5s bat %5s%%  bowl %5s%%" % (
            p, d["all"]["bat"][p]["dotPct"], d["all"]["bowl"][p]["dotPct"]))
    print("\ntop bowlers")
    for b in d["bowlers"][:4]:
        print("  %-22s %4.1f ov %3d-%d econ %5.2f dot%% %4.1f" % (
            b["name"], b["overs"], b["runs"], b["wkts"], b["econ"], b["dotPct"]))
    print("\ntop batters")
    for b in d["batters"][:5]:
        print("  %-22s %3d runs (%d) avg %-5s sr %-6s" % (
            b["name"], b["runs"], b["balls"], b["avg"], b["sr"]))
