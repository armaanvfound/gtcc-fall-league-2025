# GTCC Fall League 2025 - full match data transcribed from the CricHeroes match list PDF.
# Fields: date, round, venue, city, quota, bat1, s1, w1, ov1, bat2, s2, w2, ov2, winner, margin_txt
# bat1 = team batting first. Scores are runs/wickets; ov = overs faced (cricket notation, x.y = x overs y balls).
AJAX = ("GTCC Ajax Cricket Ground", "Ajax")
STONE = ("Stone Street Park", "Oshawa")
BROOK = ("Brooklin Memorial Park - Whitby", "Whitby")
STOM = ("Stom Street Park", "Hyderabad")
DELHI = (". Cricket Ground Of Players", "New Delhi")
AM = ("AM Cricket Ground powered by Prosfic Arena Hyderabad", "Hyderabad")
GREEN = ("Greenwoods Cricket Ground, Hyderabad", "Hyderabad")
MPS = ("MPS AJAY CRICKET GROUND .", "Hyderabad")
GYM = ("Gymkhana", "Hyderabad")
AJAXH = ("Ajax Ground", "Hyderabad")

F, SF, QF, PQF, LG = "Final", "Semi Final", "Quarter Final", "Pre Quarter Final", "League Matches"

RAW = [
 ("2025-10-12", F,   AJAX, 15, "Mavericks",119,9,15.0, "Nizam Royal Knights",102,8,15.0, "Mavericks","17 runs"),
 ("2025-10-11", SF,  AJAX, 15, "TCF",89,8,15.0, "Nizam Royal Knights",90,4,12.5, "Nizam Royal Knights","6 wickets"),
 ("2025-10-11", SF,  AJAX, 15, "Maratha Warriors - GTCC",70,10,14.3, "Mavericks",72,3,9.5, "Mavericks","7 wickets"),
 ("2025-10-05", QF,  AJAX, 15, "Harmony Strikers",150,6,15.0, "Maratha Warriors - GTCC",153,5,13.5, "Maratha Warriors - GTCC","5 wickets"),
 ("2025-10-05", QF,  AJAX, 15, "TCF",148,8,15.0, "Invincible Trailblazers",111,6,15.0, "TCF","37 runs"),
 ("2025-10-05", QF,  AJAX, 15, "Mavericks",191,7,15.0, "Durham United",85,10,12.4, "Mavericks","106 runs"),
 ("2025-10-05", QF,  AJAX, 15, "Nizam Royal Knights",96,6,15.0, "Downtown Hunterz",91,8,15.0, "Nizam Royal Knights","5 runs"),
 ("2025-10-04", PQF, AJAX, 15, "TCF",185,5,15.0, "Royal Challengers Bowmanville",94,9,15.0, "TCF","91 runs"),
 ("2025-10-04", PQF, AJAX, 15, "Team Manjummel",107,7,15.0, "Harmony Strikers",111,5,13.3, "Harmony Strikers","5 wickets"),
 ("2025-10-04", PQF, DELHI,15, "Friends United - Fall T15",100,10,14.5, "Downtown Hunterz",101,6,14.2, "Downtown Hunterz","4 wickets"),
 ("2025-10-04", PQF, DELHI,15, "Durham United",90,10,14.0, "Royal Punjab",70,10,14.4, "Durham United","20 runs"),
 ("2025-10-04", PQF, AJAX, 15, "Mavericks",109,10,14.4, "Trailblazers",67,10,13.5, "Mavericks","42 runs"),
 ("2025-10-03", PQF, AJAX, 15, "Maratha Warriors - GTCC",128,6,15.0, "Whitby Thunderbolts Gtcc fall",95,10,14.1, "Maratha Warriors - GTCC","33 runs"),
 ("2025-10-03", PQF, AJAX, 15, "Invincible Trailblazers",97,10,14.4, "DSK Friends XI",93,8,15.0, "Invincible Trailblazers","4 runs"),
 ("2025-09-28", LG,  AJAX, 15, "Friends United - Fall T15",184,6,15.0, "Golden City",59,10,9.4, "Friends United - Fall T15","125 runs"),
 ("2025-09-28", LG,  STONE,15, "Panjab XI",97,9,15.0, "Royal Challengers Bowmanville",98,2,10.2, "Royal Challengers Bowmanville","8 wickets"),
 ("2025-09-28", LG,  AJAX, 15, "Friends United - Fall T15",177,6,15.0, "Toronto Nawabs",66,9,11.5, "Friends United - Fall T15","111 runs"),
 ("2025-09-28", LG,  STOM, 15, "Royal Punjab",133,9,15.0, "Durham Strikers",125,7,15.0, "Royal Punjab","8 runs"),
 ("2025-09-28", LG,  AM,   15, "Downtown Hunterz",124,6,15.0, "Royal Challengers Bowmanville",98,10,12.5, "Downtown Hunterz","26 runs"),
 ("2025-09-28", LG,  STONE,15, "Maple Eagles",147,8,14.4, "Deccan Warriors",73,10,13.4, "Maple Eagles","74 runs"),
 ("2025-09-28", LG,  STONE,15, "FERAL XI",83,10,14.3, "Whitby Thunderbolts Gtcc fall",84,2,9.0, "Whitby Thunderbolts Gtcc fall","8 wickets"),
 ("2025-09-28", LG,  GREEN,15, "Trailblazers",120,6,15.0, "Toronto Nawabs",110,10,14.0, "Trailblazers","10 runs"),
 ("2025-09-28", LG,  STONE,15, "Mavericks",98,8,15.0, "Deccan Warriors",102,6,14.5, "Deccan Warriors","4 wickets"),
 ("2025-09-28", LG,  AJAX, 15, "Invincible Trailblazers",90,8,15.0, "Downtown Hunterz",91,7,12.2, "Downtown Hunterz","3 wickets"),
 ("2025-09-27", LG,  AJAX, 15, "Trailblazers",65,10,13.1, "Golden City",69,5,11.0, "Golden City","5 wickets"),
 ("2025-09-27", LG,  STOM, 15, "Maratha Warriors - GTCC",131,9,15.0, "Harmony Strikers",113,9,15.0, "Maratha Warriors - GTCC","18 runs"),
 ("2025-09-27", LG,  STONE,15, "Mavericks",153,8,15.0, "Royal Punjab",59,10,11.3, "Mavericks","94 runs"),
 ("2025-09-27", LG,  AJAX, 15, "Maple Eagles",106,8,15.0, "DSK Friends XI",107,6,13.0, "DSK Friends XI","4 wickets"),
 ("2025-09-27", LG,  STOM, 15, "Friends United - Fall T15",122,6,15.0, "Bowmanville Cricket Club",66,10,15.0, "Friends United - Fall T15","56 runs"),
 ("2025-09-27", LG,  STOM, 15, "Thunder Strikers",103,9,15.0, "Harmony Strikers",106,7,15.0, "Harmony Strikers","3 wickets"),
 ("2025-09-27", LG,  AJAX, 15, "Taunton Titans",66,10,15.0, "Panjab XI",68,5,9.3, "Panjab XI","5 wickets"),
 ("2025-09-27", LG,  AJAX, 15, "Oshawa Fighters",79,8,15.0, "TCF",80,3,11.3, "TCF","7 wickets"),
 ("2025-09-27", LG,  STOM, 15, "Downtown Hunterz",90,9,15.0, "North Stars T15 Fall League 2025",89,10,14.2, "Downtown Hunterz","1 run"),
 ("2025-09-27", LG,  AJAX, 15, "Avengers",77,8,13.4, "FERAL XI",81,6,9.1, "FERAL XI","4 wickets"),
 ("2025-09-26", LG,  AJAX, 15, "Birthday Boys XI",None,None,None, "Thunder Strikers",None,None,None, "Thunder Strikers","(resulted)"),
 ("2025-09-21", LG,  AJAX, 15, "Birthday Boys XI",None,None,None, "TCF",None,None,None, "TCF","(resulted)"),
 ("2025-09-21", LG,  AJAX, 15, "Whitby Thunderbolts Gtcc fall",120,8,15.0, "Redwings",122,9,15.0, "Redwings","1 wicket"),
 ("2025-09-21", LG,  AJAX, 15, "Royal Challengers Bowmanville",134,10,14.4, "North Stars T15 Fall League 2025",95,9,14.5, "Royal Challengers Bowmanville","39 runs"),
 ("2025-09-21", LG,  AJAX, 15, "DSK Friends XI",137,6,15.0, "Deccan Warriors",76,10,10.5, "DSK Friends XI","61 runs"),
 ("2025-09-21", LG,  AJAX, 15, "Invincible Trailblazers",165,6,15.0, "Taunton Titans",34,10,11.2, "Invincible Trailblazers","131 runs"),
 ("2025-09-21", LG,  STONE,15, "Nizam Royal Knights",163,6,15.0, "Bowmanville Cricket Club",66,10,14.3, "Nizam Royal Knights","97 runs"),
 ("2025-09-21", LG,  STONE,15, "Team Manjummel",112,6,15.0, "Durham United",113,1,11.4, "Durham United","9 wickets"),
 ("2025-09-21", LG,  STONE,15, "Friends United - Fall T15",87,10,13.4, "Nizam Royal Knights",92,4,10.1, "Nizam Royal Knights","6 wickets"),
 ("2025-09-20", LG,  STONE,15, "Birthday Boys XI",38,9,9.1, "Oshawa Fighters",41,1,4.1, "Oshawa Fighters","9 wickets"),
 ("2025-09-20", LG,  AJAXH,15, "Durham Strikers",90,7,15.0, "Mavericks",92,6,9.2, "Mavericks","4 wickets"),
 ("2025-09-20", LG,  STONE,15, "TCF",100,10,14.3, "Harmony Strikers",102,6,13.3, "Harmony Strikers","4 wickets"),
 ("2025-09-20", LG,  AJAX, 15, "Maple Eagles",70,10,13.2, "Royal Punjab",74,3,8.1, "Royal Punjab","7 wickets"),
 ("2025-09-20", LG,  STONE,15, "Whitby Thunderbolts Gtcc fall",115,9,15.0, "Avengers",101,5,15.0, "Whitby Thunderbolts Gtcc fall","14 runs"),
 ("2025-09-20", LG,  AJAX, 15, "Team Manjummel",101,8,15.0, "Redwings",92,10,13.3, "Team Manjummel","9 runs"),
 ("2025-09-20", LG,  STONE,15, "Trailblazers",135,7,15.0, "Friends United - Fall T15",129,6,15.0, "Trailblazers","6 runs"),
 ("2025-09-20", LG,  AJAX, 15, "Thunder Strikers",81,10,13.1, "Maratha Warriors - GTCC",82,4,11.5, "Maratha Warriors - GTCC","6 wickets"),
 ("2025-09-20", LG,  STONE,15, "North Stars T15 Fall League 2025",135,7,15.0, "Taunton Titans",112,6,15.0, "North Stars T15 Fall League 2025","23 runs"),
 ("2025-09-20", LG,  AJAX, 15, "Redwings",103,8,15.0, "Durham United",107,5,13.1, "Durham United","5 wickets"),
 ("2025-09-19", LG,  AJAX, 15, "Nizam Royal Knights",130,6,15.0, "Golden City",109,9,15.0, "Nizam Royal Knights","21 runs"),
 ("2025-09-14", LG,  AJAX, 15, "Durham United",95,9,15.0, "FERAL XI",96,8,14.4, "FERAL XI","2 wickets"),
 ("2025-09-14", LG,  AJAX, 15, "Whitby Thunderbolts Gtcc fall",100,10,15.0, "Team Manjummel",104,8,14.2, "Team Manjummel","2 wickets"),
 ("2025-09-14", LG,  AJAX, 15, "Oshawa Fighters",135,9,15.0, "Harmony Strikers",128,10,15.0, "Oshawa Fighters","7 runs"),
 ("2025-09-14", LG,  AJAX, 15, "Deccan Warriors",72,10,13.4, "Royal Punjab",73,3,8.0, "Royal Punjab","7 wickets"),
 ("2025-09-14", LG,  AJAX, 15, "Invincible Trailblazers",118,8,15.0, "Panjab XI",49,8,9.4, "Invincible Trailblazers","69 runs"),
 ("2025-09-14", LG,  AJAX, 15, "DSK Friends XI",113,10,15.0, "Durham Strikers",99,10,14.3, "DSK Friends XI","14 runs"),
 ("2025-09-13", LG,  AJAX, 12, "Mavericks",165,3,12.0, "DSK Friends XI",74,8,12.0, "Mavericks","91 runs"),
 ("2025-09-13", LG,  AJAX, 15, "TCF",122,3,15.0, "Maratha Warriors - GTCC",97,10,13.0, "TCF","25 runs"),
 ("2025-09-13", LG,  AJAX, 15, "Team Manjummel",137,8,15.0, "FERAL XI",86,10,12.2, "Team Manjummel","51 runs"),
 ("2025-09-13", LG,  BROOK,15, "Golden City",84,10,15.0, "Toronto Nawabs",61,10,13.4, "Golden City","23 runs"),
 ("2025-09-13", LG,  BROOK,15, "Maple Eagles",93,9,15.0, "Durham Strikers",67,10,13.5, "Maple Eagles","26 runs"),
 ("2025-09-13", LG,  BROOK,15, "Taunton Titans",80,9,15.0, "Royal Challengers Bowmanville",84,5,10.5, "Royal Challengers Bowmanville","5 wickets"),
 ("2025-09-13", LG,  DELHI,15, "Oshawa Fighters",94,7,15.0, "Thunder Strikers",98,7,14.3, "Thunder Strikers","3 wickets"),
 ("2025-09-13", LG,  MPS,  15, "Panjab XI",128,6,15.0, "Downtown Hunterz",95,10,14.0, "Panjab XI","33 runs"),
 ("2025-09-13", LG,  GYM,  15, "North Stars T15 Fall League 2025",109,5,15.0, "Invincible Trailblazers",111,5,13.4, "Invincible Trailblazers","5 wickets"),
 ("2025-09-13", LG,  AJAX, 15, "Bowmanville Cricket Club",65,10,15.0, "Trailblazers",67,3,7.5, "Trailblazers","7 wickets"),
 ("2025-09-13", LG,  BROOK,15, "Durham United",93,8,15.0, "Avengers",22,10,7.5, "Durham United","71 runs"),
 ("2025-09-07", LG,  STONE,15, "Golden City",134,7,15.0, "Bowmanville Cricket Club",77,10,14.0, "Golden City","57 runs"),
 ("2025-09-07", LG,  AJAX, 15, "Maratha Warriors - GTCC",195,5,15.0, "Birthday Boys XI",92,7,15.0, "Maratha Warriors - GTCC","103 runs"),
 ("2025-09-07", LG,  AJAX, 15, "Royal Punjab",126,7,15.0, "DSK Friends XI",95,10,14.1, "Royal Punjab","31 runs"),
 ("2025-09-07", LG,  STONE,15, "Team Manjummel",165,4,15.0, "Avengers",62,10,10.5, "Team Manjummel","103 runs"),
 ("2025-09-07", LG,  AJAX, 15, "Downtown Hunterz",168,8,15.0, "Taunton Titans",134,5,15.0, "Downtown Hunterz","34 runs"),
 ("2025-09-07", LG,  STONE,15, "Whitby Thunderbolts Gtcc fall",103,6,15.0, "Durham United",102,10,15.0, "Whitby Thunderbolts Gtcc fall","1 run"),
 ("2025-09-07", LG,  AJAX, 15, "Invincible Trailblazers",138,8,15.0, "Royal Challengers Bowmanville",115,7,15.0, "Invincible Trailblazers","23 runs"),
 ("2025-09-06", LG,  AJAX, 12, "Mavericks",127,8,12.0, "Maple Eagles",123,9,12.0, "Mavericks","4 runs"),
 ("2025-09-06", LG,  AJAX, 15, "Panjab XI",107,10,15.0, "North Stars T15 Fall League 2025",75,10,14.1, "Panjab XI","32 runs"),
 ("2025-09-06", LG,  AJAX, 15, "TCF",106,8,15.0, "Thunder Strikers",94,9,15.0, "TCF","12 runs"),
 ("2025-09-06", LG,  STONE,15, "Maratha Warriors - GTCC",120,8,15.0, "Oshawa Fighters",92,9,15.0, "Maratha Warriors - GTCC","28 runs"),
 ("2025-09-06", LG,  STONE,15, "Nizam Royal Knights",123,7,15.0, "Toronto Nawabs",16,10,6.1, "Nizam Royal Knights","107 runs"),
 ("2025-09-06", LG,  DELHI,15, "Redwings",121,5,15.0, "Avengers",96,6,15.0, "Redwings","25 runs"),
 ("2025-09-06", LG,  STONE,15, "Trailblazers",84,10,14.2, "Nizam Royal Knights",85,7,13.3, "Nizam Royal Knights","3 wickets"),
 ("2025-09-06", LG,  BROOK,15, "Redwings",60,10,14.3, "FERAL XI",61,7,14.4, "FERAL XI","3 wickets"),
 ("2025-09-06", LG,  BROOK,15, "Deccan Warriors",74,8,15.0, "Durham Strikers",75,2,11.3, "Durham Strikers","8 wickets"),
 ("2025-09-06", LG,  STONE,15, "Birthday Boys XI",71,6,15.0, "Harmony Strikers",73,4,7.1, "Harmony Strikers","6 wickets"),
]

def ov2dec(o):
    """14.3 overs -> 14.5 decimal overs (3 balls = half an over)."""
    if o is None: return None
    whole = int(o); balls = round((o - whole) * 10)
    return whole + balls / 6.0

MATCHES = []
for (d, rnd, (ven, city), q, b1, s1, w1, o1, b2, s2, w2, o2, win, marg) in RAW:
    MATCHES.append(dict(date=d, rnd=rnd, venue=ven, city=city, quota=q,
                        bat1=b1, s1=s1, w1=w1, ov1=o1, ov1d=ov2dec(o1),
                        bat2=b2, s2=s2, w2=w2, ov2=o2, ov2d=ov2dec(o2),
                        winner=win, loser=(b2 if win == b1 else b1), margin=marg,
                        played=s1 is not None))
