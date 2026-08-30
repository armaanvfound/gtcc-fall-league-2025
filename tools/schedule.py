"""The full 2026 league schedule, for the dashboard's schedule view.

Read from the official GTCC Fall League 2026 sheet
(docs.google.com/spreadsheets/d/16zJujkXEBeg2vYXiqXCp4p5omzQH-DoNfeKjS13qZ7w),
exported to league-raw/schedule-2026.csv. Re-export and overwrite that file to
refresh; this module only reshapes it.

The sheet holds three things, which this separates:
  - 90 group-stage matches (groups G1-G6), the fixtures proper;
  - a 17-match knockout bracket (Eliminator -> PQF -> QF -> SF -> Final), whose
    team slots are seed placeholders like "Seed 5 (GW #5)" until the groups
    finish - kept verbatim, since that IS the information;
  - the group composition, a 6x6 grid of which club sits in which group.

Our own club is written "Royal challengers blaster" in the sheet; it is
canonicalised to the name the rest of the dashboard uses so our matches can be
picked out reliably.
"""
import csv
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "league-raw" / "schedule-2026.csv"

US = "Royal Challenger Blaster"
US_IN_SHEET = "royal challengers blaster"      # matched case-insensitively anyway

GROUP_KEYS = ("G1", "G2", "G3", "G4", "G5", "G6")
KO_ROUNDS = ("Eliminator", "PQF", "QF", "SF", "Final")

# Ground strings as the sheet writes them -> a clean label + short form.
GROUNDS = {
    "STONE STREET PARK (SCHOOL SIDE PITCH)- Oshawa": ("Stone Street Park, Oshawa", "Stone Street"),
    "GTCC AJAX GROUND": ("GTCC Ajax Ground", "Ajax"),
    "GTCC - Ajax Ground": ("GTCC Ajax Ground", "Ajax"),
    "Brooklin Memorial - Whitby": ("Brooklin Memorial, Whitby", "Brooklin"),
}


def _canon(name):
    return US if (name or "").strip().lower() == US_IN_SHEET else (name or "").strip()


def _iso_and_disp(d):
    """'Aug/30/2026' -> ('2026-08-30', 'Sat 30 Aug')."""
    d = (d or "").strip()
    if not d:
        return None, None
    try:
        dt = datetime.datetime.strptime(d, "%b/%d/%Y")
        return dt.strftime("%Y-%m-%d"), dt.strftime("%a %-d %b")
    except ValueError:
        return None, d


def _ground(raw):
    raw = (raw or "").strip()
    return GROUNDS.get(raw, (raw, raw))


def build_schedule():
    if not SRC.exists():
        return None
    with SRC.open(encoding="utf-8") as fh:
        raw = list(csv.reader(fh))
    header = raw[0]
    rows = [dict(zip(header, r)) for r in raw[1:]]

    group_matches, knockouts = [], []
    for r in rows:
        no = (r.get("Match No.") or "").strip()
        grp = (r.get("Group") or "").strip()
        t1, t2 = _canon(r.get("Team 1")), _canon(r.get("Team 2"))
        if not no or not t1 or not t2:
            continue
        iso, disp = _iso_and_disp(r.get("Date"))
        gfull, gshort = _ground(r.get("Ground"))
        base = dict(
            no=int(no) if no.isdigit() else no, date=iso, disp=disp,
            day=(r.get("Day") or "").strip(), t1=t1, t2=t2,
            time=(r.get("Start Time") or "").strip(),
            ground=gfull, groundShort=gshort,
            ours=US in (t1, t2),
        )
        if grp in GROUP_KEYS:
            base["group"] = grp.replace("G", "Group ")
            group_matches.append(base)
        elif grp in KO_ROUNDS:
            base["round"] = grp
            knockouts.append(base)

    # group composition: the 6x6 grid near the foot of the sheet
    groups = {}
    header_i = next((i for i, r in enumerate(raw)
                     if [c.strip() for c in r[3:9]] == ["Group 1", "Group 2", "Group 3",
                                                        "Group 4", "Group 5", "Group 6"]), None)
    if header_i is not None:
        names = raw[header_i][3:9]
        for gi, gname in enumerate(names):
            members = []
            for r in raw[header_i + 1:]:
                cell = _canon(r[3 + gi]) if len(r) > 3 + gi else ""
                if cell:
                    members.append(cell)
            groups[gname] = members

    our_group = next((g for g, m in groups.items() if US in m), None)
    our_matches = [m for m in group_matches if m["ours"]]

    return dict(
        source="GTCC Fall League 2026 official schedule",
        groupMatches=group_matches,
        knockouts=knockouts,
        groups=groups,
        ourGroup=our_group,
        ourMatches=our_matches,
        totals=dict(group=len(group_matches), knockout=len(knockouts),
                    teams=sum(len(m) for m in groups.values()) or None,
                    first=group_matches[0]["date"] if group_matches else None,
                    last=(knockouts[-1]["date"] if knockouts else
                          group_matches[-1]["date"] if group_matches else None)),
    )


if __name__ == "__main__":
    import json
    s = build_schedule()
    print("group matches:", s["totals"]["group"], "| knockouts:", s["totals"]["knockout"])
    print("our group:", s["ourGroup"], "->", s["groups"].get(s["ourGroup"]))
    print("our matches:")
    for m in s["ourMatches"]:
        opp = m["t2"] if m["t1"] == US else m["t1"]
        print("  #%-3s %s  vs %-24s %s @ %s" % (m["no"], m["disp"], opp, m["time"], m["groundShort"]))
