"""Our 2026 campaign: group, fixtures and format.

Transcribed from the official GTCC Fall League 2026 schedule sheet
(docs.google.com/spreadsheets/d/16zJujkXEBeg2vYXiqXCp4p5omzQH-DoNfeKjS13qZ7w),
exported as CSV and filtered to the matches involving us. Dates, times and
grounds are exactly as published; the sheet is the source of truth.

`known2025` maps a 2026 opponent to its name in last season's data, and only
where the name matches exactly. Nothing here guesses at renames: "United
Punjab" is not assumed to be 2025's "Royal Punjab" or "Panjab XI", and our own
"Royal Challenger Blaster" is emphatically not 2025's "Royal Challengers
Bowmanville" - a different club we have real data on. An opponent we cannot
identify with certainty is reported as unscouted rather than matched loosely,
because a confident profile built on the wrong team is worse than none.
"""

TEAM = "Royal Challenger Blaster"
GROUP = "Group 5"

# Every side in our group, us included.
GROUP_TEAMS = [
    "Royal Challenger Blaster", "Durham United", "Invincible Trailblazers",
    "South Warriors", "Lisa Challengers", "United Punjab",
]

# 2026 opponent -> the exact team name in tools/data.py (2025 season).
# Only exact matches; see the module docstring.
KNOWN_2025 = {
    "Durham United": "Durham United",
    "Invincible Trailblazers": "Invincible Trailblazers",
}

# Ground as written in the 2026 sheet -> the venue name in the 2025 data, so
# each fixture can carry last season's read on how that ground plays.
VENUE_2025 = {
    "Stone Street Park": "Stone Street Park",
    "GTCC Ajax Ground": "GTCC Ajax Cricket Ground",
}

# Our five group matches, in order.
FIXTURES = [
    dict(no=5,  date="2026-09-05", disp="Sat 5 Sep",  time="09:05",
         opp="United Punjab",           ground="Stone Street Park"),
    dict(no=36, date="2026-09-12", disp="Sat 12 Sep", time="11:10",
         opp="Durham United",           ground="GTCC Ajax Ground"),
    dict(no=47, date="2026-09-13", disp="Sun 13 Sep", time="15:05",
         opp="South Warriors",          ground="Stone Street Park"),
    dict(no=62, date="2026-09-19", disp="Sat 19 Sep", time="17:25",
         opp="Lisa Challengers",        ground="Stone Street Park"),
    dict(no=75, date="2026-09-26", disp="Sat 26 Sep", time="13:45",
         opp="Invincible Trailblazers", ground="GTCC Ajax Ground"),
]

FORMAT = dict(
    teams=36, groups=6, groupSize=6, perTeam=5, leagueMatches=90,
    advancePerGroup=3, advanceTotal=18,
    leagueStart="2026-08-30", leagueEnd="2026-09-27",
    # Seeding, which is what makes finishing position worth chasing.
    seeding=[
        ("Win the group", "Seeds 1-6", "straight into the pre-quarters against the lowest seeds"),
        ("Finish second", "Seeds 7-12", "straight into the pre-quarters, tougher draw"),
        ("Third, top 2 by NRR", "Seeds 13-14", "straight into the pre-quarters"),
        ("Third, bottom 4 by NRR", "Eliminator", "must win a knockout on 3 Oct just to reach the pre-quarters"),
    ],
    playoffs=[
        ("3 Oct", "Eliminators + Pre-quarters day 1"),
        ("4 Oct", "Pre-quarters day 2"),
        ("10 Oct", "Quarter-finals"),
        ("11 Oct", "Semi-finals"),
        ("12 Oct", "Final"),
    ],
)


def build_season(phases=None, venues=None):
    """Assemble the 2026 block, attaching what we know about each opponent."""
    vmap = {v["venue"]: v for v in (venues or [])}
    fixtures = []
    for f in FIXTURES:
        old = KNOWN_2025.get(f["opp"])
        prof = (phases or {}).get("teams", {}).get(old) if old else None
        v2025 = vmap.get(VENUE_2025.get(f["ground"], ""))
        fixtures.append(dict(
            f,
            scouted=bool(prof),
            name2025=old,
            venue=dict(n=v2025["n"], batFirstPct=v2025["pct"], avg1=v2025["avg1"]) if v2025 else None,
        ))
    return dict(team=TEAM, group=GROUP, groupTeams=GROUP_TEAMS,
                fixtures=fixtures, format=FORMAT,
                scoutedCount=sum(1 for f in fixtures if f["scouted"]))


if __name__ == "__main__":
    import json
    print(json.dumps(build_season(), indent=1))
