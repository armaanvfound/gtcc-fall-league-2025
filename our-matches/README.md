# our-matches

Every match Royal Challenger Blaster has played, league or friendly, one file
per match. `tools/ourmatches.py` turns these into the "How we have actually
played" section and into the form line that section 09's match plan reads.

## Adding a match

1. Open the match on CricHeroes and go to the **Commentary** tab.
2. Run the extractor below in the browser console, once per innings (use the
   innings dropdown to switch). Pass the phase boundaries for the format:
   15 overs -> `__agg(5,10)`, 12 overs -> `__agg(4,8)`, 10 overs -> `__agg(3,7)`.
3. Copy the numbers into a new `<matchid>.json` in the shape below.
4. Reconcile against the **Scorecard** tab before committing - see Checks.
5. `python3 tools/build.py`.

```js
window.__agg=function(ppEnd,midEnd){
  var L=document.querySelector('main').innerText.split('\n').map(s=>s.trim());
  var balls=[];
  for(var i=0;i<L.length;i++){
    var m=L[i].match(/^(\d+)\.(\d)$/); if(!m) continue;
    var d=(L[i+1]||'').split(' AI:')[0];
    var N=+m[1], b=+m[2], ov=(b===0)?N:N+1;      // ball N.0 ends over N
    var extra=null, runs=0, wkt=0, r;
    if(/,\s*wide/i.test(d)){ extra='wd'; r=d.match(/wide,\s*(\d+)\s*runs?/i); runs=1+(r?+r[1]:0); }
    else if(/\(no ball\)/i.test(d)){ extra='nb'; runs=1;
      if(/,\s*FOUR/.test(d)) runs+=4; else if(/,\s*SIX/.test(d)) runs+=6;
      else { r=d.match(/\(no ball\),\s*(\d+)\s*runs?/i); if(r) runs+=+r[1]; } }
    else if(/,\s*OUT[\s,]/.test(d)){ wkt=1; r=d.match(/,\s*(\d+)\s*runs?/); runs=r?+r[1]:0; }
    else if(/,\s*SIX/.test(d)) runs=6;
    else if(/,\s*FOUR/.test(d)) runs=4;
    else if(/,\s*no run/i.test(d)) runs=0;
    else { r=d.match(/,\s*(\d+)\s*runs?/); runs=r?+r[1]:0; }
    var bo=d.match(/^([^,]+?)\s+to\s+/);
    balls.push({ov:ov,runs:runs,wkt:wkt,extra:extra,bowler:bo?bo[1]:'?'});
  }
  function ph(o){ return o<=ppEnd?'pp':(o<=midEnd?'mid':'death'); }
  var out={tot:{legal:0,dots:0,runs:0,wkt:0,wdBalls:0,wdRuns:0,nb:0},
           ph:{pp:[0,0,0,0],mid:[0,0,0,0],death:[0,0,0,0]},bw:{}};
  balls.forEach(function(x){
    var p=ph(x.ov), P=out.ph[p];
    out.tot.runs+=x.runs; out.tot.wkt+=x.wkt; P[2]+=x.runs; P[3]+=x.wkt;
    if(!out.bw[x.bowler]) out.bw[x.bowler]={pp:[0,0,0,0],mid:[0,0,0,0],death:[0,0,0,0]};
    var a=out.bw[x.bowler][p]; a[2]+=x.runs; a[3]+=x.wkt;
    if(x.extra==='wd'){ out.tot.wdBalls++; out.tot.wdRuns+=x.runs; return; }
    if(x.extra==='nb'){ out.tot.nb++; return; }
    out.tot.legal++; P[0]++; a[0]++;
    if(x.runs===0){ out.tot.dots++; P[1]++; a[1]++; }
  });
  return out;
};
__agg(5,10)
```

## Checks before committing

The extractor is regex over commentary prose, so verify it rather than trust it.
Every innings recorded so far passes all four:

- **Runs** equal the innings total on the scorecard.
- **Legal balls** equal the overs faced (`13.4` -> `13*6+4 = 82`).
- **Wickets** equal the number in the scorecard's fall-of-wickets list.
- **Per-bowler runs** equal each bowler's figures. Note the scorecard's own
  bowling table renders without its runs column - recover it as
  `economy x overs`, which is exact.

Two known traps, both already handled by the code above:

- The old regex matched `OUT` case-insensitively and so read `Outside Edge` as a
  wicket. It is case-sensitive now; keep it that way.
- The extractor credits a wicket to whoever bowled the delivery, so a **run out**
  arrives against the bowler. Move it: `ourBowling[...].w` and the bowler's phase
  array carry bowler-credited wickets only, while `theirInnings.phases` counts
  every wicket including run outs. That is why the two can differ by one.

Balls faced by the batters will exceed legal deliveries by the number of
no-balls, which is correct - a batter faces a no-ball, the over does not count it.

## File shape

```jsonc
{
 "mid": "26716186",              // CricHeroes match id, and the filename
 "date": "2026-08-19",
 "opp": "FERAL XI",
 "venue": "Ajax Cricket Club Ground, Ajax",
 "competition": "Friendly",      // or "GTCC Fall League 2026"
 "isLeague": false,              // true only for competitive league matches
 "quota": 15,                    // overs per side
 "phaseBounds": [5, 10],         // last over of the powerplay, last of the middle
 "toss": "FERAL XI won the toss and chose to bat",
 "result": "won",                // won | lost | tied
 "margin": "3 wickets",
 "url": "https://cricheroes.com/...",
 "ourInnings": {
   "order": 2,                   // 1 = we batted first
   "runs": 131, "wkts": 7, "oversText": "13.4", "balls": 82,
   "wideRuns": 7, "noBalls": 1,
   "phases": {"pp": [30,15,52,3], "mid": [30,7,50,3], "death": [22,10,29,1]},
   "batting": [["Name", runs, balls, fours, sixes, wasDismissed], ...]
 },
 "theirInnings": {
   "order": 1,
   "runs": 127, "wkts": 7, "oversText": "15.0", "balls": 90,
   "wideRuns": 10, "noBalls": 1,
   "phases": {"pp": [30,13,46,2], "mid": [30,13,37,3], "death": [30,11,44,2]},
   "ourBowling": {
     "Bowler Name": {"o": 3, "r": 16, "w": 2,
       "ph": {"pp": [6,3,7,1], "mid": [6,2,4,0], "death": [6,4,5,1]}}
   }
 }
}
```

Every phase array is `[legal balls, dots, runs, wickets]`.

## What the model will and will not do with these

Only 15-over matches are set against the league par in `tools/phases.py`. A
12-over innings has no fifth-over powerplay and an 8-over hit-out has no death,
so comparing either to a 15-over par would manufacture a finding. Shorter
matches still appear in the match log and still feed player careers, where a
ball faced and a run conceded mean the same thing whatever the quota.

A dot ball here is a legal delivery off which **no runs at all** were scored.
CricHeroes counts a bye or leg bye as a dot for the batter; we do not, since a
run was scored. That is the only definitional gap between our count and the
number in their `0s` column.
