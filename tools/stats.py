"""Computes every number the report shows, from tools/data.py.

Score-based analysis uses 15-over matches only (a couple of group games were
played over 12 overs, so their totals are not comparable). Net run rate charges
an all-out innings the full quota, as the competition regulations do.
"""
import collections, statistics
from data import MATCHES

ORDER = ['League Matches', 'Pre Quarter Final', 'Quarter Final', 'Semi Final', 'Final']
SHORT = {'League Matches': 'League', 'Pre Quarter Final': 'Pre-QF', 'Quarter Final': 'QF',
         'Semi Final': 'SF', 'Final': 'Final'}

# Registered squad, from the team's own public CricHeroes roster page.
# Names only - no contact details go on a public site.
SQUAD = dict(
    team='Royal Challenger Blaster', city='Pickering', captain='Jemish Virendra Patel',
    players=['Jemish Virendra Patel', 'Armaan Wadhwa', 'Jay', 'Jay Vasani',
             'Jeetmanyu Bawra', 'Jonty Patel', 'Kalpesh Saraiya', 'Nikhil Das T',
             'Pankhil Patel', 'Patel Happy', 'Rudresh Bhanushali', 'Sabar',
             'Saurabh Patel', 'Yash Chauhan'],
)


def build_payload():
    ALL = MATCHES
    P = [m for m in ALL if m['played']]
    P15 = [m for m in P if m['quota'] == 15]
    teams = sorted({m['bat1'] for m in ALL} | {m['bat2'] for m in ALL})

    RF = collections.defaultdict(float); OF = collections.defaultdict(float)
    RA = collections.defaultdict(float); OA = collections.defaultdict(float)
    S = collections.defaultdict(collections.Counter)
    log = collections.defaultdict(list)

    for m in ALL:
        lg = m['rnd'] == 'League Matches'
        for t in (m['bat1'], m['bat2']):
            S[t]['P'] += 1
            if lg: S[t]['lgP'] += 1
        S[m['winner']]['W'] += 1; S[m['loser']]['L'] += 1
        if lg: S[m['winner']]['lgW'] += 1; S[m['loser']]['lgL'] += 1
        for me, opp, s, w, ovd, ov, first in (
                (m['bat1'], m['bat2'], m['s1'], m['w1'], m['ov1d'], m['ov1'], True),
                (m['bat2'], m['bat1'], m['s2'], m['w2'], m['ov2d'], m['ov2'], False)):
            if m['played']:
                eff = m['quota'] if w == 10 else ovd
                RF[me] += s; OF[me] += eff; RA[opp] += s; OA[opp] += eff
                S[me]['allout'] += (w == 10)
                S[me]['bat1' if first else 'bat2'] += 1
                if m['winner'] == me: S[me]['bat1W' if first else 'bat2W'] += 1
            log[me].append(dict(date=m['date'], rnd=SHORT[m['rnd']], opp=opp, first=first,
                                won=(m['winner'] == me), s=s, w=w, ov=ov,
                                os=(m['s2'] if first else m['s1']),
                                ow=(m['w2'] if first else m['w1']),
                                oov=(m['ov2'] if first else m['ov1']),
                                margin=m['margin'], venue=m['venue']))

    deepest = {t: max(ORDER.index(m['rnd']) for m in ALL if t in (m['bat1'], m['bat2'])) for t in teams}
    finals = [m for m in ALL if m['rnd'] == 'Final']
    champ = finals[0]['winner'] if finals else None
    runner = finals[0]['loser'] if finals else None
    nrr = {t: (RF[t]/OF[t] - RA[t]/OA[t]) if OF[t] and OA[t] else 0.0 for t in teams}
    ko = {t for m in ALL if m['rnd'] != 'League Matches' for t in (m['bat1'], m['bat2'])}

    def finish(t):
        if t == champ: return 'Champion'
        if t == runner: return 'Runner-up'
        return {'Semi Final': 'Semi-final', 'Quarter Final': 'Quarter-final',
                'Pre Quarter Final': 'Pre-quarter-final',
                'League Matches': 'Missed knockouts'}[ORDER[deepest[t]]]

    rank = sorted(teams, key=lambda t: (-deepest[t], -S[t]['lgW'], -nrr[t]))
    TEAMS = []
    for i, t in enumerate(rank, 1):
        s = S[t]
        scores1 = [m['s1'] for m in P15 if m['bat1'] == t]
        conc = [(m['s2'] if m['bat1'] == t else m['s1']) for m in P15 if t in (m['bat1'], m['bat2'])]
        TEAMS.append(dict(
            rank=i, team=t, lgW=s['lgW'], lgL=s['lgL'], W=s['W'], L=s['L'],
            nrr=round(nrr[t], 2), rf=round(RF[t]/OF[t], 2) if OF[t] else 0,
            ra=round(RA[t]/OA[t], 2) if OA[t] else 0,
            finish=finish(t), ko=(t in ko), allout=s['allout'], inns=s['bat1'] + s['bat2'],
            bat1=s['bat1'], bat1W=s['bat1W'], bat2=s['bat2'], bat2W=s['bat2W'],
            avg1=round(statistics.mean(scores1)) if scores1 else None,
            avgConc=round(statistics.mean(conc)) if conc else None,
            log=sorted(log[t], key=lambda x: x['date'])))

    bands = []
    for lo_, hi_, lab in [(0, 79, 'under 80'), (80, 99, '80–99'), (100, 119, '100–119'),
                          (120, 139, '120–139'), (140, 159, '140–159'), (160, 9999, '160+')]:
        sub = [m for m in P15 if lo_ <= m['s1'] <= hi_]
        w = sum(1 for m in sub if m['winner'] == m['bat1'])
        bands.append(dict(label=lab, won=w, n=len(sub),
                          pct=round(w/len(sub)*100) if sub else 0))

    venues = []
    for v, _ in collections.Counter(m['venue'] for m in P15).most_common():
        sub = [m for m in P15 if m['venue'] == v]
        if len(sub) < 5: continue
        w = sum(1 for m in sub if m['winner'] == m['bat1'])
        venues.append(dict(venue=v, n=len(sub), pct=round(w/len(sub)*100),
                           avg1=round(statistics.mean([m['s1'] for m in sub]))))

    bf = sum(1 for m in P if m['winner'] == m['bat1'])
    hi = [m for m in P15 if m['s1'] >= 120]; lo = [m for m in P15 if m['s1'] < 120]
    outq = [m for m in P15 if m['w1'] < 10]; aout = [m for m in P15 if m['w1'] == 10]
    close = [m for m in P if (m['winner'] == m['bat1'] and m['s1']-m['s2'] <= 10)
             or (m['winner'] == m['bat2'] and 10-m['w2'] <= 2)]
    blow = [m for m in P if (m['winner'] == m['bat1'] and m['s1']-m['s2'] >= 50)
            or (m['winner'] == m['bat2'] and m['ov2d'] <= m['quota']*0.7)]

    # groups: connected components of the league-stage fixture graph
    adj = collections.defaultdict(set)
    for m in ALL:
        if m['rnd'] == 'League Matches':
            adj[m['bat1']].add(m['bat2']); adj[m['bat2']].add(m['bat1'])
    seen = set(); comps = []
    for t in sorted(adj):
        if t in seen: continue
        comp = set(); stack = [t]
        while stack:
            x = stack.pop()
            if x in comp: continue
            comp.add(x); stack += [y for y in adj[x] if y not in comp]
        seen |= comp; comps.append(comp)
    comps.sort(key=lambda g: -max(S[t]['lgW'] for t in g))
    GROUPS = [dict(name="Group " + "ABCDEFGH"[i], rows=[
        dict(team=t, W=S[t]['lgW'], L=S[t]['lgL'], nrr=round(nrr[t], 2),
             through=(t in ko), finish=finish(t))
        for t in sorted(g, key=lambda t: (-S[t]['lgW'], -nrr[t]))])
        for i, g in enumerate(comps)]

    h2h = {frozenset((m['bat1'], m['bat2'])): m['winner']
           for m in ALL if m['rnd'] == 'League Matches'}
    pair = frozenset(('Panjab XI', 'Royal Challengers Bowmanville'))

    dates = sorted(m['date'] for m in ALL)
    LEAGUE = dict(
        matches=len(ALL), scored=len(P), scored15=len(P15), teams=len(teams),
        first=dates[0], last=dates[-1],
        batFirstW=bf, batFirstPct=round(bf/len(P)*100) if P else 0,
        avg1=round(statistics.mean([m['s1'] for m in P15])),
        med1=round(statistics.median([m['s1'] for m in P15])),
        avg2=round(statistics.mean([m['s2'] for m in P15])),
        bands=bands, venues=venues,
        hi120=dict(w=sum(1 for m in hi if m['winner'] == m['bat1']), n=len(hi)),
        lo120=dict(w=sum(1 for m in lo if m['winner'] == m['bat1']), n=len(lo)),
        outQuota=dict(w=sum(1 for m in outq if m['winner'] == m['bat1']), n=len(outq),
                      avg=round(statistics.mean([m['s1'] for m in outq]))),
        allOut=dict(w=sum(1 for m in aout if m['winner'] == m['bat1']), n=len(aout),
                    avg=round(statistics.mean([m['s1'] for m in aout]))),
        alloutPct=round(sum(1 for m in P15 for w in (m['w1'], m['w2']) if w == 10)/(2*len(P15))*100),
        closePct=round(len(close)/len(P)*100), blowPct=round(len(blow)/len(P)*100),
        scores1=sorted(m['s1'] for m in P15),
        groups=GROUPS,
        bubble=dict(
            qualified=sorted([dict(team=t, nrr=round(nrr[t], 2)) for t in teams
                              if S[t]['lgW'] == 3 and S[t]['lgL'] == 2 and t in ko],
                             key=lambda x: -x['nrr']),
            missed=sorted([dict(team=t, nrr=round(nrr[t], 2)) for t in teams
                           if S[t]['lgW'] == 3 and S[t]['lgL'] == 2 and t not in ko],
                          key=lambda x: -x['nrr'])),
        h2hNote=(dict(a='Panjab XI', b='Royal Challengers Bowmanville', winner=h2h[pair])
                 if pair in h2h else None),
    )
    out = dict(league=LEAGUE, teams=TEAMS)
    try:
        from phases import build_phases
        out['phases'] = build_phases()
    except Exception:
        out['phases'] = None
    out['squad'] = SQUAD
    try:
        from season import build_season
        out['season'] = build_season(out['phases'], LEAGUE['venues'])
    except Exception:
        out['season'] = None
    try:
        from ourmatches import build_ours
        out['ours'] = build_ours()
    except Exception:
        out['ours'] = None
    # Per-player league data. Optional: the pages fall back to team-level
    # scouting when league-raw/performances.tsv has not been collected yet.
    try:
        from league_players import build_players
        out['players'] = build_players()
    except Exception:
        out['players'] = None
    return out
