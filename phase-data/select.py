import sys, json, collections
sys.path.insert(0, 'tools')
from data import MATCHES

# URLs from the spreadsheet-derived parse (has cricheroes urls)
raw = json.load(open('/private/tmp/claude-501/-Users-armaanwadhwa-Desktop-Automation-Scripts/fbd84d25-1c26-4e4b-bd0a-0794c581a766/scratchpad/matches.json'))
url_by = {}
for m in raw:
    key = (m['date'], frozenset((m['bat1'], m['bat2'])))
    url_by[key] = m['url'].replace('/summary', '/commentary')

played = [m for m in MATCHES if m['played']]
for m in played:
    m['url'] = url_by.get((m['date'], frozenset((m['bat1'], m['bat2']))))
    m['mid'] = m['url'].split('/scorecard/')[1].split('/')[0] if m['url'] else None
missing = [m for m in played if not m['url']]
print("played:", len(played), " url matched:", len(played)-len(missing), " missing:", len(missing))

KO = [m for m in played if m['rnd'] != 'League Matches']            # 14
league = [m for m in played if m['rnd'] == 'League Matches']         # 72
teams = sorted({m['bat1'] for m in played} | {m['bat2'] for m in played})

sel = list(KO)
cover = collections.Counter()
for m in sel:
    cover[m['bat1']] += 1; cover[m['bat2']] += 1

TARGET = 40
# Greedy: repeatedly add the league match that most improves coverage of
# under-represented teams, breaking ties toward extreme 1st-innings totals.
def score(m):
    need = sum(max(0, 2 - cover[t]) for t in (m['bat1'], m['bat2']))   # reward covering teams seen <2x
    return need
remaining = [m for m in league]
while len(sel) < TARGET and remaining:
    remaining.sort(key=lambda m: (-score(m), -abs(m['s1'] - 114)))     # extremes of 1st-inns total
    pick = remaining.pop(0)
    sel.append(pick)
    cover[pick['bat1']] += 1; cover[pick['bat2']] += 1

sel.sort(key=lambda m: (['League Matches','Pre Quarter Final','Quarter Final','Semi Final','Final'].index(m['rnd']), m['date']))
print(f"\nSELECTED {len(sel)} matches. Team coverage: min {min(cover.values())}, max {max(cover.values())}")
uncov = [t for t in teams if cover[t] == 0]
print("teams with 0 appearances:", uncov if uncov else "none — all 30 covered")
print("teams appearing once:", sum(1 for t in teams if cover[t]==1), " twice+:", sum(1 for t in teams if cover[t]>=2))
tot1 = sorted(m['s1'] for m in sel)
print(f"1st-innings totals span: {tot1[0]}–{tot1[-1]}  (sample of all played: {min(m['s1'] for m in played)}–{max(m['s1'] for m in played)})")
print("bat-first wins:", sum(1 for m in sel if m['winner']==m['bat1']), " chase wins:", sum(1 for m in sel if m['winner']==m['bat2']))

out = [dict(mid=m['mid'], date=m['date'], rnd=m['rnd'], bat1=m['bat1'], bat2=m['bat2'],
            s1="%d/%d"%(m['s1'],m['w1']), s2="%d/%d"%(m['s2'],m['w2']),
            winner=m['winner'], url=m['url']) for m in sel]
json.dump(out, open('phase-data/selection.json','w'), indent=1)
print("\nwrote phase-data/selection.json")
for i,m in enumerate(out,1):
    print(f"{i:2}. {m['date']} {m['rnd'][:5]:<5} {m['mid']:>9}  {m['bat1'][:24]:<24} v {m['bat2'][:24]}")
