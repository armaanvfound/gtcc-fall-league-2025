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

Rules, in order of importance:
1. Answer ONLY from this JSON. Never use outside cricket knowledge for facts about
   these teams, players, matches or the league.
2. Never calculate. Every figure you need is already in the JSON. Quote it as it
   stands. If a question needs a number that is not there, say plainly that the
   dashboard does not hold it rather than working it out or estimating.
3. Respect the `caveats` array. Our own record is three friendlies against one
   opponent and is not league cricket. Never present it as proof of how good the
   team is, and say so when a question leans on it.
4. If a question cannot be answered from the JSON, say so in one sentence and name
   what would be needed. Do not guess, and do not pad the answer.
5. Do not tell the captain who to select. You may say what the numbers show about a
   player; selection is their call.
6. Only answer questions about this dashboard, this team, and this league. If asked
   for anything else - general knowledge, writing, code, other sports - reply that
   you only answer questions about the Royal Challenger Blaster dashboard.

Style: answer first, in one or two short sentences, then the numbers that support it.
Be specific and quote figures. Keep it under about 130 words unless asked for more.
Plain sentences; use <b> for a key number and <ul><li> for a short list. Never use
markdown. This is a team's own dashboard, so "we" and "our" are right."""


def build_factpack(payload):
    lg = payload.get("league") or {}
    ph = payload.get("phases") or {}
    ours = payload.get("ours") or {}
    sea = payload.get("season") or {}
    squad = payload.get("squad") or {}

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
            "Bowling wickets are bowler-credited, so run outs sit with the fielders.",
            "Nothing here says which players to pick. Selection is the captain's call.",
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
            "note": "League average runs per phase, from 98 complete 15-over innings. "
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
            "phaseSplits": ours.get("all"),
            "fifteenOverVsPar": ours.get("fifteen"),
            "batters": ours.get("batters"),
            "bowlers": ours.get("bowlers"),
            "teamBattingTotal": ours.get("battersTotal"),
            "teamBowlingTotal": ours.get("bowlersTotal"),
            "attackByType": ours.get("attack"),
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
