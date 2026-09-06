/* Captures ball-by-ball for ONE of our matches and prints the our-matches JSON
 * fragments, fully reconciled. Paste into the console on the match's
 * Commentary tab on cricheroes.com, then run  __rcb.capture()  once per innings.
 *
 * WHY THIS EXISTS. Everything else on the dashboard comes from scorecards,
 * which CricHeroes embeds in the page HTML. Phase splits (powerplay / middle /
 * death) do not - they need every ball, and CricHeroes renders the commentary
 * client-side only. So this is the one step of a sync that needs a person:
 * the tab must be VISIBLE (Chrome in the foreground). A background tab is
 * throttled and never paints the commentary at all; you will read zero balls.
 *
 * HOW
 *   1. Open the match -> Commentary. Keep Chrome in front.
 *   2. Paste this file. Run  __rcb.capture()  -> it stores the innings shown.
 *   3. Use the innings dropdown (top-left of the commentary panel) to switch
 *      to the other innings - a REAL click; synthetic clicks do not open it -
 *      then run  __rcb.capture()  again.
 *   4. Run  __rcb.emit(quota)  e.g. __rcb.emit(15). It prints the JSON for
 *      ourInnings / theirInnings and a reconciliation table. Every line of
 *      that table must say OK before the numbers go into a match file.
 *
 * CONVENTIONS (each one was a bug once)
 *   - CricHeroes numbers ball N.0 as the LAST ball of over N; N.1-N.5 belong
 *     to over N+1. Get this wrong and every phase boundary shifts a ball.
 *   - Team phases count EVERY wicket including run outs, and every run
 *     including byes: [balls, dots, runs, wkts].
 *   - Per-bowler phases are BOWLER-CREDITED: no run-out wickets, no bye or
 *     leg-bye runs. Wides and no-balls ARE charged to the bowler. This is what
 *     makes each bowler's phase runs and wickets sum exactly to their card.
 *   - A dot is a legal delivery with no runs at all (CricHeroes counts a bye
 *     as a batter's dot; we do not).
 *   - Per-batter phases are [balls faced, dots, runs off the bat, 4s, 6s];
 *     a wide is not a ball faced.
 */
(function () {
  const RCB = 'Royal Challenger Blaster';
  const store = { inns: [] };

  function lines() {
    return (document.body.innerText || '').split('\n').map(s => s.trim()).filter(Boolean)
      .reduce((a, l, i, arr) => {
        if (/^\d+\.\d+$/.test(l) && arr[i + 1] && /\sto\s/.test(arr[i + 1]))
          a.push(l + ' | ' + arr[i + 1].split(' AI:')[0]);
        return a;
      }, []).reverse();                                  // page lists newest first
  }
  function overOf(s) { const [o, b] = s.split('.').map(Number); return b === 0 ? o : o + 1; }
  function phaseOf(o, q) { const a = q === 15 ? 5 : q === 12 ? 4 : 3, b = q === 15 ? 10 : q === 12 ? 8 : 7;
    return o <= a ? 'pp' : (o <= b ? 'mid' : 'death'); }

  function ball(ev) {
    const wide = /\bwide\b/i.test(ev), no = /\(no ball\)/i.test(ev);
    const bye = /leg bye|,\s*bye\b/i.test(ev);
    let r = 0;
    if (/\bSIX\b/.test(ev)) r = 6; else if (/\bFOUR\b/.test(ev)) r = 4;
    else { const m = ev.match(/(\d+)\s*runs?\b/); if (m) r = +m[1]; }
    const runout = /run out/i.test(ev), out = /\bOUT\b/.test(ev);
    let total, offBat, charged;
    if (wide)      { total = 1 + r; offBat = 0; charged = 1 + r; }
    else if (no)   { total = 1 + r; offBat = r; charged = 1 + r; }
    else if (bye)  { total = r;     offBat = 0; charged = 0; }
    else           { total = r;     offBat = r; charged = r; }
    return { legal: !wide && !no, total, offBat, charged, out,
             bowlerWkt: out && !runout, dot: !wide && !no && total === 0,
             four: /\bFOUR\b/.test(ev) && !wide, six: /\bSIX\b/.test(ev) && !wide,
             wideRuns: wide ? 1 + r : 0, noBall: no ? 1 : 0, byeRuns: bye ? r : 0 };
  }

  function tally(L, q) {
    const ph = { pp: [0, 0, 0, 0], mid: [0, 0, 0, 0], death: [0, 0, 0, 0] };
    const bowl = {}, bat = {};
    let runs = 0, balls = 0, wkts = 0, wd = 0, nb = 0, by = 0;
    for (const l of L) {
      const [ov, rest] = l.split(' | ');
      const m = rest.match(/^(.+?) to (.+?), (.*)$/); if (!m) continue;
      const p = phaseOf(overOf(ov), q), B = ball(m[3]);
      runs += B.total; if (B.legal) balls++; if (B.out) wkts++;
      wd += B.wideRuns; nb += B.noBall; by += B.byeRuns;
      if (B.legal) ph[p][0]++; if (B.dot) ph[p][1]++; ph[p][2] += B.total; if (B.out) ph[p][3]++;
      const w = bowl[m[1]] = bowl[m[1]] || { pp: [0, 0, 0, 0], mid: [0, 0, 0, 0], death: [0, 0, 0, 0] };
      if (B.legal) w[p][0]++; if (B.dot) w[p][1]++; w[p][2] += B.charged; if (B.bowlerWkt) w[p][3]++;
      const b = bat[m[2]] = bat[m[2]] || { pp: [0, 0, 0, 0, 0], mid: [0, 0, 0, 0, 0], death: [0, 0, 0, 0, 0] };
      if (B.legal) b[p][0]++; if (B.dot) b[p][1]++; b[p][2] += B.offBat; if (B.four) b[p][3]++; if (B.six) b[p][4]++;
    }
    return { ph, bowl, bat, runs, balls, wkts, wd, nb, by };
  }

  function whoBats(L) {
    // the batting side is whoever is NOT bowling; RCB bowls if our names bowl
    const bowlers = new Set(L.map(l => (l.split(' | ')[1].match(/^(.+?) to /) || [])[1]));
    const rcbBowls = [...bowlers].some(n => /Jeetmanyu|Jemish|Kalpesh|Patel Happy|Armaan Wadhwa|Saurabh|Sabar|Jay\b/.test(n || ''));
    return rcbBowls ? 'them' : 'us';
  }

  window.__rcb = {
    capture() {
      const L = lines();
      if (!L.length) { console.warn('[rcb] no balls read - is Chrome in the foreground and the commentary painted?'); return; }
      const side = whoBats(L);
      store.inns = store.inns.filter(i => i.side !== side);
      store.inns.push({ side, L });
      console.log('%c[rcb] captured ' + side + ' batting: ' + L.length + ' deliveries. ' +
        (store.inns.length === 2 ? 'Both innings held - run __rcb.emit(quota).' : 'Now switch the innings dropdown and capture again.'),
        'color:#B23A32;font-weight:bold');
    },
    emit(quota) {
      quota = quota || 15;
      const us = store.inns.find(i => i.side === 'us'), them = store.inns.find(i => i.side === 'them');
      if (!us || !them) { console.warn('[rcb] need both innings captured first'); return; }
      const U = tally(us.L, quota), T = tally(them.L, quota);
      const bowlingOut = {};
      for (const [n, ph] of Object.entries(T.bowl)) {
        const o = ph.pp[0] + ph.mid[0] + ph.death[0];
        bowlingOut[n] = { o: Math.floor(o / 6) + (o % 6) / 10, r: ph.pp[2] + ph.mid[2] + ph.death[2],
                          w: ph.pp[3] + ph.mid[3] + ph.death[3], ph };
      }
      const out = {
        ourInnings: { runs: U.runs, wkts: U.wkts, balls: U.balls, wideRuns: U.wd, noBalls: U.nb,
                      byeRuns: U.by, phases: U.ph, battingPhases: U.bat },
        theirInnings: { runs: T.runs, wkts: T.wkts, balls: T.balls, wideRuns: T.wd, noBalls: T.nb,
                        byeRuns: T.by, phases: T.ph, ourBowling: bowlingOut },
      };
      console.log(JSON.stringify(out, null, 1));
      console.table([
        { check: 'our runs = sum of phases', value: U.runs, ok: U.ph.pp[2] + U.ph.mid[2] + U.ph.death[2] === U.runs },
        { check: 'our balls = batting phase balls', value: U.balls,
          ok: Object.values(U.bat).reduce((s, b) => s + b.pp[0] + b.mid[0] + b.death[0], 0) === U.balls },
        { check: 'their balls = bowling phase balls', value: T.balls,
          ok: Object.values(T.bowl).reduce((s, b) => s + b.pp[0] + b.mid[0] + b.death[0], 0) === T.balls },
      ]);
      console.log('%c[rcb] Now compare runs/wkts/balls and EVERY bowler\'s r/w against the Scorecard tab. ' +
        'Bowler lines must match exactly (run outs not credited, byes not charged). Then set allOut on ' +
        'each innings from the scorecard and write our-matches/<id>.json.', 'color:#B23A32');
      return out;
    },
  };
  console.log('%c[rcb] ready. Run __rcb.capture() on each innings, then __rcb.emit(15).', 'color:#B23A32;font-weight:bold');
})();
