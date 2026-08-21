"""Builds facts.json - the compact, precomputed brief the chatbot answers from.

The assistant is deliberately not allowed to calculate anything. Every number it
can quote is computed here, by the same pipeline that renders the pages, and it
is told to answer only from this file. That is what makes the answers dependable:
the hard part (reconciling ball-by-ball data, averaging phases, working out net
run rate) has already happened and been checked, so the model's only job is to
find the right number and put it in a sentence.

Size matters, because the whole pack rides in the system prompt on every
question. The full page payload is ~74k characters, most of it the 30 teams'
match logs, which no one will ask about. Trimmed and rounded, this lands near
25k characters (~7k tokens) - small enough to send every time and to cache.
"""
import copy
import datetime
import json


def _r(v, nd=0):
    """Round for display; keep None as None so 'not measured' stays visible."""
    if v is None:
        return None
    return round(v, nd) if nd else round(v)


def _phase_block(d, keys=("pp", "mid", "death")):
    return {k: _r(d.get(k), 1) for k in keys}


# The assistant's instructions live here, in the data file, so the two callers
# cannot drift apart: the team proxy builds the prompt server-side, and the
# bring-your-own-key path builds it in the browser. Both read this string.
PROMPT = """You answer questions about the Royal Challenger Blaster cricket dashboard.

The JSON below is the complete set of facts available to you. It was computed from
ball-by-ball data and reconciled against the scorecards, so the numbers in it are
correct and final.

There are two different things you do, and the difference matters. FACTS are the
numbers, and they come only from the JSON. JUDGEMENT is what you make of them, and
that is yours to give - freely, and without hedging.

Rules, in order of importance:
1. Facts come ONLY from this JSON. Never use outside cricket knowledge for facts
   about these teams, players, matches or the league.
2. Never calculate a figure. Every number you need is already in the JSON; quote it
   as it stands. If a question needs a number that is not there, say plainly that
   the dashboard does not hold it - and then answer anyway from what it does hold.
   A missing number is never a reason to withhold a view.
3. ALWAYS GIVE THE RECOMMENDATION. This team is deciding something before a toss,
   so "it depends", "that is the captain's call" and "consider both options" are
   failures, not caution. When asked what to do - bat or bowl, who opens the
   bowling, who to hold back, which phase to attack, who to target - name the call
   in your first sentence, in plain words, then the numbers behind it. If the data
   is thin, still make the call: give your best read, say it is a best read, and
   name the one thing that would change it. Never end by handing the decision back.
4. WHERE THE PACK ALREADY DECIDES SOMETHING, QUOTE ITS DECISION. `tossPolicy`
   holds the standing toss call and `opponents2025[team].target` the target for
   that side. These are what the dashboard's own pages show, so answering
   anything else makes the assistant contradict the site it speaks for. If you
   think the numbers point the other way, say so as a note AFTER giving the
   dashboard's call - never instead of it.
5. Own the judgement, and keep it visibly separate from the numbers. The figures are
   the dashboard's and they are final; the call is yours. Say "I would" and "we
   should". Never dress a judgement up as if it were a measured fact.
6. Respect the `caveats` array. Our own record is three friendlies against one
   opponent and is not league cricket - say so when a question leans on it, then
   still make the call on the evidence there is. A caveat qualifies a recommendation;
   it never replaces one.
7. Only answer questions about this dashboard, this team, and this league. If asked
   for anything else - general knowledge, writing, code, other sports - reply that
   you only answer questions about the Royal Challenger Blaster dashboard.

Style: lead with the answer or the call, in one or two short sentences, then the
numbers that support it. Be specific and quote figures. Keep it under about 150
words unless asked for more. Plain sentences. This renders as HTML, so use <b> for a key number or
the call itself and <ul><li> for a short list. NEVER use markdown - no **bold**,
no ##headings, no *bullets*. Asterisks appear literally on screen and look broken. This is a team's own
dashboard, so "we" and "our" are right."""


# Two different wicket counts live in this pack and they are NOT the same number.
# A phase total counts every wicket that fell in those overs, run outs included;
# a bowler's column counts only what the bowler is credited with. Left both named
# "wkts", they get mixed up - our death phase reads 5 one way and 4 the other, and
# an answer can quote one line's runs beside the other line's wickets. So each is
# renamed to say which it is, and the caveats spell out the difference.
def _rename_wkts(block, new, phases=("pp", "mid", "death")):
    """Rename 'wkts' to `new` in each phase dict of `block`. Returns a copy."""
    if not isinstance(block, dict):
        return block
    out = copy.deepcopy(block)
    for ph in phases:
        d = out.get(ph)
        if isinstance(d, dict) and "wkts" in d:
            d[new] = d.pop("wkts")
    return out


def _phases_all(side):
    """A phaseSplits/fifteen side ({bat, bowl, ...}) with team-wicket naming."""
    if not isinstance(side, dict):
        return side
    out = copy.deepcopy(side)
    for k in ("bat", "bowl"):
        if k in out:
            out[k] = _rename_wkts(out[k], "wktsAll")
    return out


def _bowler_credited(obj):
    """A bowler-shaped dict ({..., wkts, ph:{pp,mid,death}}) with credited naming.

    Both the career total and each phase are renamed, so every wicket number in a
    bowling context reads `wktsBowler` without exception. A rule with no exceptions
    is the one that survives being skim-read.
    """
    if not isinstance(obj, dict):
        return obj
    out = copy.deepcopy(obj)
    if "wkts" in out:
        out["wktsBowler"] = out.pop("wkts")
    if isinstance(out.get("ph"), dict):
        out["ph"] = _rename_wkts(out["ph"], "wktsBowler")
    return out

def _attack_credited(attack):
    """The pace/spin table: {rows: [bowler-shaped, ...]}."""
    if not isinstance(attack, dict) or not isinstance(attack.get("rows"), list):
        return attack
    out = copy.deepcopy(attack)
    out["rows"] = [_bowler_credited(r) for r in out["rows"]]
    return out


# The pages already decide the toss, and they decide it the same way every time:
# bat. Leaving the assistant to re-derive that from the raw splits let it answer
# "bowl first" to the question the dashboard answers "bat" - the one thing a
# single source of truth must never do. So the call ships as a fact, with the
# same target rule the match-plan page uses (setTarget in template.html).
def _target_for(t, death_par):
    """Mirror of setTarget(): 140 if they finish hard, 125 if they cannot, else 130."""
    base = 130
    bat = (t or {}).get("bat") or {}
    if bat.get("death") is not None and (bat.get("deathn") or 0) >= 3 and death_par:
        d = round(bat["death"] - death_par)
        if d >= 4:
            return {"target": 140, "because": "they finish hard", "deathVsPar": d}
        if d <= -4:
            return {"target": 125, "because": "they do not accelerate", "deathVsPar": d}
    d = (round(bat["death"] - death_par)
         if bat.get("death") is not None and death_par else 0)
    return {"target": base, "because": "they finish about par", "deathVsPar": d}


# Player data goes in as fixed-order tuples, not objects. Thirty teams of named
# fields would add roughly 25k characters to a pack that rides on every single
# question; the tuples plus one legend line cost about a third of that and the
# model reads them just as well.
def _players_block(pl):
    if not pl or not pl.get("teams"):
        return None
    out = {
        "_legend": {
            "bat": "[name, runs, standoutInnings, bestScore, strikeRate]",
            "bowl": "[name, wickets, spells, bestFigures, economy, dotPct]",
        },
        "whatThisIs": (
            "The top three batting and top three bowling performances of each of "
            "%d matches - %d batting and %d bowling efforts in all. These are NOT "
            "season averages: a player's quiet matches are not in here and players "
            "who never had a standout day do not appear. Runs mean 'runs when he "
            "went big'. Use it to say who is dangerous and how, never to quote "
            "anyone's average."
        ) % (pl["matches"], pl["battingPerformances"], pl["bowlingPerformances"]),
        "teams": {},
    }
    for name, t in pl["teams"].items():
        out["teams"][name] = {
            "bat": [[b["name"], b["runs"], b["inns"], b["best"], b["sr"]]
                    for b in t["batters"][:3]],
            "bowl": [[w["name"], w["wkts"], w["inns"], w["best"], w["econ"], w["dotPct"]]
                     for w in t["bowlers"][:3]],
        }
    return out


def build_factpack(payload):
    lg = payload.get("league") or {}
    ph = payload.get("phases") or {}
    ours = payload.get("ours") or {}
    sea = payload.get("season") or {}
    squad = payload.get("squad") or {}

    # Stated rather than left implicit: the gap between the two counts is the
    # run outs, and quoting it is what stops the difference reading as an error.
    _all_ph = (ours.get("all") or {}).get("bowl") or {}
    _cred_ph = (ours.get("bowlersTotal") or {}).get("ph") or {}
    _sum = lambda d: sum((d.get(k) or {}).get("wkts") or 0 for k in ("pp", "mid", "death"))
    _wa, _wb = _sum(_all_ph), _sum(_cred_ph)
    _wkt_tally = (
        "Across our %d matches so far that is %d wktsAll against %d wktsBowler. "
        % (len(ours.get("matches") or []), _wa, _wb) if _wa or _wb else ""
    )

    pack = {
        "_prompt": PROMPT,
        "generated": datetime.date.today().isoformat(),
        "team": squad.get("team", "Royal Challenger Blaster"),

        # Read these first - they bound what any answer may claim.
        "caveats": [
            "Our own record is 3 friendlies against a single opponent (FERAL XI), "
            "in three different formats. None of it is league cricket. Treat our "
            "numbers as habits, not as proof of how good we are.",
            "The 2025 league numbers are a different, solid basis: 88 matches, all "
            "read ball by ball, so statements about how the league behaves are well "
            "supported.",
            "Only 15-over matches are compared against league par. A 12-over innings "
            "has no fifth-over powerplay and an 8-over hit-out has no death.",
            "A dot ball here is a legal delivery off which no runs at all were "
            "scored. CricHeroes counts a bye as a dot for the batter; we do not.",
            "`dangerMen2025` is a threat list, not a form guide: each match's "
            "three best batting and three best bowling efforts. Quiet games are "
            "absent, so never present those runs as an average or those figures "
            "as a season record. Say 'when he has gone big' or 'his standout "
            "spells'.",
            "Two wicket counts appear and they differ. In phase blocks "
            "(phaseSplits, fifteenOverVsPar) the field is `wktsAll`: every wicket "
            "that fell in those overs, run outs included. In a bowler's own figures "
            "and in teamBowlingTotal the field is `wktsBowler`: only what the bowler "
            "is credited with, so run outs sit with the fielders. " + _wkt_tally +
            "Never quote one beside the other, and say which you mean.",
            "Runs follow the same split: a bowler's runs (career and per phase) are "
            "bowler-credited and exclude byes and leg byes, while team phase blocks "
            "include them. So teamBowlingTotal can trail phaseSplits.bowl by a few "
            "runs; the gap is byes, recorded per innings as byeRuns.",
            "Recommendations are wanted, including on selection and on who bowls "
            "when. Make the call from these numbers and say how strongly the data "
            "supports it. The captain decides in the end, but never withhold a view "
            "or answer with 'it depends'.",
        ],

        "league2025": {
            "matches": lg.get("matches"), "teams": lg.get("teams"),
            "window": [lg.get("first"), lg.get("last")], "oversPerSide": 15,
            "winLine": {
                "line": 120,
                "postedOver120": lg.get("hi120"),
                "postedUnder120": lg.get("lo120"),
                "meaning": "Posting 120+ batting first won ~94% of the time; under 120, "
                           "the chasing side won about two thirds.",
            },
            "batFirst": {"winPct": lg.get("batFirstPct"), "wins": lg.get("batFirstW")},
            "avgFirstInnings": lg.get("avg1"), "medianFirstInnings": lg.get("med1"),
            "avgSecondInnings": lg.get("avg2"),
            "allOutPct": lg.get("alloutPct"),
            "closeMatchPct": lg.get("closePct"), "blowoutPct": lg.get("blowPct"),
            "scoreBands": lg.get("bands"),
            "venues": lg.get("venues"),
        },

        "phasePar2025": {
            "note": "League average runs per phase. Each phase is averaged over every "
                    "innings that completed THAT phase, so the samples differ: powerplay "
                    "167 innings, middle 155, death 98 (only innings that reached over 15). One innings has no over-by-over record "
                    "(Friends United 184/6 v Golden City, 2025-09-28) and sits outside "
                    "phase averages, though it counts in results and win-line bands. "
                    "Powerplay = overs 1-5, middle = 6-10, death = 11-15.",
            "all": _phase_block(ph.get("all", {})),
            "winners": _phase_block(ph.get("won", {})),
            "losers": _phase_block(ph.get("lost", {})),
            "decisivePhase": ph.get("decisive"),
            "gapWinnersMinusLosers": ph.get("gaps"),
            "battingFirst": _phase_block(ph.get("bat1", {})),
            "chasing": _phase_block(ph.get("bat2", {})),
            "sample": ph.get("sample"),
        },

        "us": {
            "record": ours.get("record"),
            "matches": ours.get("matches"),
            "phaseSplits": _phases_all(ours.get("all")),
            "fifteenOverVsPar": _phases_all(ours.get("fifteen")),
            "batters": ours.get("batters"),
            "bowlers": [_bowler_credited(b) for b in (ours.get("bowlers") or [])],
            "teamBattingTotal": ours.get("battersTotal"),
            "teamBowlingTotal": _bowler_credited(ours.get("bowlersTotal")),
            "attackByType": _attack_credited(ours.get("attack")),
            "battingByHand": ours.get("handSplit"),
            "squad": squad.get("players"),
            "captain": squad.get("captain"),
        },

        "season2026": {
            "group": sea.get("group"),
            "groupTeams": sea.get("groupTeams"),
            "fixtures": sea.get("fixtures"),
            "format": sea.get("format"),
            "scoutedOpponents": sea.get("scoutedCount"),
        },

        # Every 2025 side's phase profile, compressed. Used for opponent questions.
        "opponents2025": {},

        "conditions": {
            "note": "Day-level weather for match days, averaged 07:00-18:00. Match "
                    "start times are not in our data, so this is not per-match.",
            "days": (ph.get("weather") or [])[:14],
        },

        "paceVsSpin2025": ph.get("bowlTypes"),

        # Who actually hurts you, by team. See _legend for the tuple order.
        "dangerMen2025": _players_block(payload.get("players")),

        # THE STANDING CALL. Quote this; do not re-derive it.
        "tossPolicy": {
            "ifWeWinTheToss": "BAT FIRST",
            "isThisEverBowlFirst": "No. There is no ground in this competition "
                                   "where chasing is the better bet.",
            "why": "Batting first won %s%% of decided matches in 2025, and totals of "
                   "120+ were defended %s%% of the time." % (
                       lg.get("batFirstPct"),
                       int(round((lg.get("hi120") or {}).get("w", 0)
                                 / max(1, (lg.get("hi120") or {}).get("n", 1)) * 100))),
            "ifWeLoseTheTossAndTheyBat": "We bowl first; the job is keeping them under 120.",
            "ifWeLoseTheTossAndTheyBowl": "We bat first anyway - this is the plan we wanted.",
            "defaultTarget": 130,
            "perOpponentTarget": "See opponents2025[team].target - already computed.",
            "note": "This is the dashboard's own recommendation and every page shows "
                    "it. Never answer 'bowl first' to a won toss, and never present "
                    "a contrary reading of the same numbers as the recommendation.",
        },
    }

    for name, t in (ph.get("teams") or {}).items():
        entry = {}
        if t.get("bat"):
            b = t["bat"]
            entry["batting"] = dict(_phase_block(b), total=_r(b.get("total"), 1),
                                    innings=b.get("n"))
        if t.get("bowl"):
            w = t["bowl"]
            entry["bowlingConceded"] = dict(_phase_block(w), total=_r(w.get("total"), 1),
                                            innings=w.get("n"))
        if entry:
            entry.update(_target_for(t, (ph.get("all") or {}).get("death")))
            pack["opponents2025"][name] = entry

    return pack


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import build_payload
    fp = build_factpack(build_payload())
    s = json.dumps(fp, separators=(",", ":"))
    print("fact pack: %d chars  (~%d tokens)" % (len(s), len(s) / 3.5))
    for k, v in fp.items():
        vs = json.dumps(v, separators=(",", ":"))
        print("   %-16s %7d chars" % (k, len(vs)))
