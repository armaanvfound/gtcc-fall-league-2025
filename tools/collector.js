/* Collects full scorecards from CricHeroes. Paste into the browser console.
 *
 * WHY IT RUNS IN A BROWSER. CricHeroes is behind Cloudflare - plain curl gets a
 * 403 challenge - and it renders detail client-side, so there is no JSON API to
 * call. Inside a tab that has already passed the challenge, same-origin fetch
 * works perfectly. 86 matches came back in 89 seconds.
 *
 * WHAT IT COLLECTS. Each match page embeds `scoreCardData`: both innings in
 * full. Every batter with runs, balls, boundaries, batting hand and how they got
 * out; every bowler with overs, maidens, runs, wickets, dots, boundaries
 * conceded and extras. That is the real scorecard, so the stats built from it
 * are real season figures - not the three-best-performances summary that is also
 * on the page, and not the tournament leaderboard, which is behind CricHeroes PRO.
 *
 * HOW TO RUN
 *   1. Open the tournament's Matches tab and click "Completed".
 *   2. Open DevTools (Cmd-Opt-J) and paste this whole file into the console.
 *   3. It scrolls to load every match, collects, and downloads a .tsv.
 *   4. Then, in the repo:  python3 tools/sync.py
 *
 * Concurrency is 3 with a 300ms gap. That was measured: 6-at-once had a quarter
 * of requests come back 429, 3 with a gap had none. Please do not raise it.
 */
(async () => {
  const CONC = 3, GAP = 300;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const log = (...a) => console.log('%c[rcb]', 'color:#B23A32;font-weight:bold', ...a);

  if (!location.hostname.endsWith('cricheroes.com')) {
    console.error('[rcb] Run this on a cricheroes.com tournament Matches page.');
    return;
  }

  async function get(url, tries = 4) {
    for (let a = 0; a < tries; a++) {
      const r = await fetch(url, { credentials: 'include' });
      if (r.status === 429) { await sleep(800 * (a + 1)); continue; }   // backoff
      return r.ok ? await r.text() : null;
    }
    return null;
  }

  // ---- 1. a reliable team_id -> name map -------------------------------------
  // Built from the tournament's own teams page. Reading names out of each match
  // instead leaves gaps: a match whose best performers all came from one side
  // never names the other, which silently produced "team10750303" rows once.
  const tourney = (location.pathname.match(/^\/tournament\/\d+\/[^/]+/) || [])[0];
  const TEAM = {};
  if (tourney) {
    const tp = await get(tourney + '/teams');
    if (tp) for (const m of tp.replace(/\\"/g, '"').matchAll(/"team_id":(\d+),"team_name":"([^"]+)"/g))
      TEAM[m[1]] = m[2];
  }
  log(Object.keys(TEAM).length + ' teams mapped');

  // ---- 2. discover every completed match --------------------------------------
  const ids = () => [...new Set([...document.querySelectorAll('a')]
    .map(a => (a.getAttribute('href') || '').split('?')[0])
    .filter(h => h.startsWith('/scorecard/'))
    .map(h => h.split('/')[2]))];

  // The list is paged behind a "Load more" button, not infinite scroll - and a
  // notification modal sits over it. Its "Later" button has to be clicked first
  // or every click lands on the overlay and the count never moves off 12. The
  // modal can also reappear, so it is dismissed on each pass.
  //
  // The tournament slug must be the REAL one here. A wrong-but-present slug
  // still renders the page and still serves scorecard fetches, but the server
  // action behind "Load more" rejects it and the list silently stops at 12.
  log('expanding the match list...');
  const btnsMatching = re => [...document.querySelectorAll('button')]
    .filter(b => re.test(b.textContent || ''));
  for (let k = 0; k < 80; k++) {
    const later = btnsMatching(/^\s*later\s*$/i)[0];
    if (later) later.click();
    const more = btnsMatching(/load more/i)[0];
    if (!more) break;
    const before = ids().length;
    more.scrollIntoView({ block: 'center' });
    await sleep(250);
    more.click();
    let waited = 0;
    while (waited < 9000 && ids().length === before) { await sleep(400); waited += 400; }
    if (ids().length === before) { log('  list stopped at ' + before); break; }
    if (k % 4 === 0) log('  ' + ids().length + ' matches');
  }

  const MATCHES = ids();
  if (!MATCHES.length) {
    console.error('[rcb] No matches found. Are you on the Matches tab with "Completed" selected?');
    return;
  }
  log('found ' + MATCHES.length + ' matches');

  // ---- 3. parse each scorecard -------------------------------------------------
  const clean = v => String(v == null ? '' : v).replace(/[\t\r\n]/g, ' ');
  const rows = [];
  const TID = location.pathname.split('/')[2];
  const TNAME = (document.querySelector('h1') || {}).textContent
                ? document.querySelector('h1').textContent.trim()
                : ('tournament ' + TID);

  function parse(html, id) {
    const un = html.replace(/\\"/g, '"');
    const arrAt = idx => {
      let d = 0, e = -1;
      for (let k = idx; k < un.length; k++) {
        const c = un[k];
        if (c === '[') d++;
        else if (c === ']') { d--; if (!d) { e = k + 1; break; } }
      }
      try { return JSON.parse(un.slice(idx, e)); } catch (x) { return null; }
    };
    const overs = (un.match(/"overs":(\d+)/) || [])[1] || '';
    const ballType = (un.match(/"ball_type":"([A-Z]+)"/) || [])[1] || '';
    const i = un.indexOf('"scoreCardData":[');
    if (i < 0) return false;
    const sc = arrAt(un.indexOf('[', i));
    if (!sc || !sc.length) return false;

    // per-match fallback for any id the tournament page did not list
    const local = {};
    for (const m of un.matchAll(/"team_id":(\d+),"team_name":"([^"]+)"/g)) local[m[1]] = m[2];
    const nameOf = tid => TEAM[String(tid)] || local[String(tid)] || ('team' + tid);

    sc.forEach((inn, idx) => {
      const batTeam = nameOf(inn.team_id);
      const other = sc[(idx + 1) % sc.length];
      const bowlTeam = other ? nameOf(other.team_id) : '?';
      for (const b of (inn.batting || []))
        rows.push(['B', id, idx + 1, clean(batTeam), clean(b.name), b.runs, b.balls,
                   b['4s'], b['6s'], b.SR, clean(b.batting_hand), clean(b.how_to_out),
                   b.player_id, TID, clean(TNAME), overs, ballType].join('\t'));
      for (const w of (inn.bowling || []))
        rows.push(['W', id, idx + 1, clean(bowlTeam), clean(w.name), w.overs, w.maidens,
                   w.runs, w.wickets, w['0s'], w['4s'], w['6s'], w.wide, w.noball,
                   w.economy_rate, w.player_id, TID, clean(TNAME), overs, ballType].join('\t'));
    });
    return true;
  }

  const failed = [];
  let idx = 0, done = 0;
  const t0 = Date.now();

  async function worker() {
    while (idx < MATCHES.length) {
      const id = MATCHES[idx++];
      try {
        const html = await get('/scorecard/' + id + '/x/y/scorecard');
        if (html && parse(html, id)) {
          done++;
          if (done % 10 === 0) log('  ' + done + '/' + MATCHES.length);
        } else failed.push(id);
      } catch (e) { failed.push(id); }
      await sleep(GAP);
    }
  }
  await Promise.all(Array.from({ length: CONC }, worker));

  // one slower retry pass - failures are nearly always transient rate limits
  if (failed.length) {
    log('retrying ' + failed.length + '...');
    for (const id of failed.splice(0, failed.length)) {
      const html = await get('/scorecard/' + id + '/x/y/scorecard', 5);
      if (html && parse(html, id)) done++; else failed.push(id);
      await sleep(600);
    }
  }

  // ---- 4. hand the file to the browser ----------------------------------------
  const text = rows.join('\n') + '\n';
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: 'text/tab-separated-values' }));
  a.download = 'rcb-' + TID + '.tsv';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);

  log('done: ' + done + '/' + MATCHES.length + ' matches, ' + rows.length + ' rows, ' +
      ((Date.now() - t0) / 1000).toFixed(0) + 's');
  if (failed.length) console.warn('[rcb] still missing:', failed.join(','));
  log('saved rcb-' + TID + '.tsv - now run:  python3 tools/sync.py --add ~/Downloads/rcb-' + TID + '.tsv');
  window.__rcb = { text, rows, failed };   // in case the download is blocked
})();
