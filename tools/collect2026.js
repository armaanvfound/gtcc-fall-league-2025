/* Refreshes the 2026 results file. Paste into the browser console on any
 * cricheroes.com page (a scorecard or the tournament page both work).
 *
 * Finds every completed match of GTCC Fall League 2026 (tournament 2167460),
 * fetches each full scorecard, and downloads rcb-results-2026.tsv. Then:
 *
 *     cp ~/Downloads/rcb-results-2026.tsv league-raw/results-2026.tsv
 *     python3 tools/build.py
 *     git add -A && git commit -m "2026 results" && git push
 *
 * Run it after each round. Two matches took ~3 seconds; a full season of 90
 * will take about a minute at this pacing. Concurrency stays at 2 with a gap -
 * measured on the 2025 harvest, faster gets 429s.
 */
(async () => {
  const TID = 2167460;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const clean = v => String(v == null ? '' : v).replace(/[\t\r\n]/g, ' ');
  const log = (...a) => console.log('%c[rcb26]', 'color:#B23A32;font-weight:bold', ...a);

  if (!location.hostname.endsWith('cricheroes.com')) {
    console.error('[rcb26] Run this on a cricheroes.com page.');
    return;
  }

  async function get(u, t = 4) {
    for (let a = 0; a < t; a++) {
      const r = await fetch(u, { credentials: 'include' });
      if (r.status === 429) { await sleep(1000 * (a + 1)); continue; }
      return r.ok ? await r.text() : null;
    }
    return null;
  }
  const arrAt = (un, idx) => {
    let d = 0, e = -1;
    for (let k = idx; k < un.length; k++) {
      const c = un[k];
      if (c === '[') d++;
      else if (c === ']') { d--; if (!d) { e = k + 1; break; } }
    }
    try { return JSON.parse(un.slice(idx, e)); } catch (x) { return null; }
  };

  // 1. every completed match id
  const lp = await get(`/tournament/${TID}/x/matches/past-matches`);
  const lun = (lp || '').replace(/\\"/g, '"');
  let i = -1, list = null;
  while ((i = lun.indexOf('"data":[', i + 1)) !== -1) {
    const a = arrAt(lun, lun.indexOf('[', i));
    if (a && a.length && a[0] && a[0].match_id && (!list || a.length > list.length)) list = a;
  }
  const ids = (list || []).map(m => m.match_id);
  if (!ids.length) { console.error('[rcb26] no completed matches found'); return; }
  log(ids.length + ' completed matches');

  // NOTE: the tournament page lazy-loads past 12 matches. Once more than 12
  // are complete, open the tournament's Matches -> Past tab, scroll to load
  // them all, and run this there - it also reads ids off the page's links.
  const domIds = [...new Set([...document.querySelectorAll('a')]
    .map(a => (a.getAttribute('href') || '').split('?')[0])
    .filter(h => h.startsWith('/scorecard/')).map(h => h.split('/')[2]))];
  const ALL = [...new Set([...ids, ...domIds.map(Number).filter(Boolean)])];
  if (ALL.length > ids.length) log('+' + (ALL.length - ids.length) + ' more from the page');

  // 2. each full scorecard
  const L = [];
  let done = 0;
  for (const id of ALL) {
    const un = ((await get(`/scorecard/${id}/x/y/scorecard`)) || '').replace(/\\"/g, '"');
    const sc = arrAt(un, un.indexOf('[', un.indexOf('"scoreCardData":[')));
    if (!sc || sc.length !== 2) { log('skip ' + id + ' (no card)'); continue; }
    const nm = {};
    for (const m of un.matchAll(/"team_id":(\d+),"team_name":"([^"]+)"/g)) nm[m[1]] = m[2];
    const g = re => (un.match(re) || [])[1] || '';
    L.push(['M', id, g(/"start_datetime":"([^"T]+)/), clean(g(/"ground_name":"([^"]+)"/)),
      clean(g(/"toss_details":"([^"]{0,140})"/)), clean(g(/"winning_team":"([^"]+)"/)),
      clean(g(/"win_by":"([^"]{0,60})"/)), g(/"match_type":"([^"]+)"/)].join('\t'));
    sc.forEach((inn, ix) => {
      const I = inn.inning || {};
      const bat = nm[String(inn.team_id)] || ('team' + inn.team_id);
      const other = sc[(ix + 1) % sc.length];
      const bowl = other ? (nm[String(other.team_id)] || ('team' + other.team_id)) : '?';
      // is_allout is CricHeroes' own flag and the only reliable one: a
      // 10-a-side team is all out at 9 down, and NRR hangs on knowing it.
      L.push(['I', id, ix + 1, clean(bat), I.total_run, I.total_wicket,
              I.overs_played, I.total_extra, I.is_allout ? 1 : 0].join('\t'));
      for (const b of (inn.batting || []))
        L.push(['B', id, ix + 1, clean(bat), clean(b.name), b.runs, b.balls, b['4s'],
                b['6s'], b.SR, clean(b.batting_hand), clean(b.how_to_out), b.player_id].join('\t'));
      for (const w of (inn.bowling || []))
        L.push(['W', id, ix + 1, clean(bowl), clean(w.name), w.overs, w.maidens, w.runs,
                w.wickets, w['0s'], w['4s'], w['6s'], w.wide, w.noball,
                w.economy_rate, w.player_id].join('\t'));
    });
    done++;
    if (done % 10 === 0) log(done + '/' + ALL.length);
    await sleep(500);
  }

  const text = L.join('\n') + '\n';
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: 'text/tab-separated-values' }));
  a.download = 'rcb-results-2026.tsv';
  document.body.appendChild(a); a.click(); a.remove();
  log('done: ' + done + ' matches, ' + L.length + ' rows. Now: cp ~/Downloads/rcb-results-2026.tsv league-raw/results-2026.tsv && python3 tools/build.py');
})();
