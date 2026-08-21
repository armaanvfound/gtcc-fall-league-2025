/* Collects per-player league data from CricHeroes. Paste into the browser console.
 *
 * WHY IT RUNS IN A BROWSER. CricHeroes is behind Cloudflare - plain curl gets a
 * 403 challenge - and it renders its detail client-side, so there is no JSON API
 * to call. Inside a tab that has already passed the challenge, same-origin fetch
 * works perfectly: 30 team pages came back in 2.8 seconds. So this runs there.
 *
 * WHAT IT COLLECTS. Each match page carries a `best_performances` block in its
 * HTML: the top three batting and top three bowling efforts of that match. The
 * full scorecard and the tournament leaderboard are not available to us - the
 * leaderboard is behind CricHeroes PRO - so this is the deepest per-player data
 * that is actually reachable. It is a threat list, not a set of averages, and
 * everything downstream is labelled that way.
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

  // ---- 1. discover every completed match on the page -------------------------
  const ids = () => [...new Set([...document.querySelectorAll('a')]
    .map(a => (a.getAttribute('href') || '').split('?')[0])
    .filter(h => h.startsWith('/scorecard/'))
    .map(h => h.split('/')[2]))];

  log('scrolling to load the full match list...');
  let seen = -1, stable = 0;
  while (stable < 3) {
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(900);
    const n = ids().length;
    if (n === seen) stable++; else { stable = 0; seen = n; log('  ' + n + ' matches so far'); }
  }
  const MATCHES = ids();
  if (!MATCHES.length) {
    console.error('[rcb] No matches found. Are you on the Matches tab with "Completed" selected?');
    return;
  }
  log('found ' + MATCHES.length + ' matches');

  // ---- 2. fetch each and pull out best_performances ---------------------------
  async function get(url, tries = 4) {
    for (let a = 0; a < tries; a++) {
      const r = await fetch(url, { credentials: 'include' });
      if (r.status === 429) { await sleep(800 * (a + 1)); continue; }   // backoff
      return r.ok ? await r.text() : null;
    }
    return null;
  }

  function bestPerformances(html) {
    // the payload is embedded with escaped quotes; brace-match the object out
    const un = html.replace(/\\"/g, '"');
    const i = un.indexOf('"best_performances":');
    if (i < 0) return null;
    let depth = 0, start = un.indexOf('{', i), end = -1;
    for (let k = start; k < un.length; k++) {
      const c = un[k];
      if (c === '{') depth++;
      else if (c === '}') { depth--; if (!depth) { end = k + 1; break; } }
    }
    try { return JSON.parse(un.slice(start, end)); } catch (e) { return null; }
  }

  const lines = [], failed = [];
  let idx = 0, done = 0;
  const t0 = Date.now();

  async function worker() {
    while (idx < MATCHES.length) {
      const id = MATCHES[idx++];
      try {
        const html = await get('/scorecard/' + id + '/x/y/scorecard');
        const bp = html && bestPerformances(html);
        if (!bp) { failed.push(id); }
        else {
          for (const b of (bp.batting || []))
            lines.push(['B', id, b.inning, b.team_name, b.player_name, b.runs, b.balls,
                        b['4s'], b['6s'], b.strike_rate, b.is_out, b.player_id].join('\t'));
          for (const w of (bp.bowling || []))
            lines.push(['W', id, w.inning, w.team_name, w.player_name, w.overs, w.runs,
                        w.wickets, w.economy_rate, w['0s'], w.maidens, w.player_id].join('\t'));
          done++;
          if (done % 10 === 0) log('  ' + done + '/' + MATCHES.length);
        }
      } catch (e) { failed.push(id); }
      await sleep(GAP);
    }
  }
  await Promise.all(Array.from({ length: CONC }, worker));

  // one retry pass - the failures are nearly always transient rate limits
  if (failed.length) {
    log('retrying ' + failed.length + ' that failed...');
    const again = failed.splice(0, failed.length);
    for (const id of again) {
      const html = await get('/scorecard/' + id + '/x/y/scorecard', 5);
      const bp = html && bestPerformances(html);
      if (!bp) { failed.push(id); continue; }
      for (const b of (bp.batting || []))
        lines.push(['B', id, b.inning, b.team_name, b.player_name, b.runs, b.balls,
                    b['4s'], b['6s'], b.strike_rate, b.is_out, b.player_id].join('\t'));
      for (const w of (bp.bowling || []))
        lines.push(['W', id, w.inning, w.team_name, w.player_name, w.overs, w.runs,
                    w.wickets, w.economy_rate, w['0s'], w.maidens, w.player_id].join('\t'));
      done++;
      await sleep(600);
    }
  }

  // ---- 3. hand the file to the browser ---------------------------------------
  const text = lines.join('\n') + '\n';
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: 'text/tab-separated-values' }));
  a.download = 'rcb-performances.tsv';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);

  log('done: ' + done + '/' + MATCHES.length + ' matches, ' + lines.length + ' rows, ' +
      ((Date.now() - t0) / 1000).toFixed(0) + 's');
  if (failed.length) console.warn('[rcb] still missing:', failed.join(','));
  log('saved rcb-performances.tsv - now run:  python3 tools/sync.py');
  window.__rcb = { text, lines, failed };   // in case the download is blocked
})();
