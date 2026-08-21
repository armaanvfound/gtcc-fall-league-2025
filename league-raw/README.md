# Keeping the league data current

Re-run this whenever new matches have been played. It takes about three minutes,
almost all of it waiting.

## 1. Collect (in the browser)

CricHeroes sits behind Cloudflare and renders its detail client-side, so there is
no API to call and `curl` gets a 403. The collector therefore runs inside a tab
that has already passed the challenge, where same-origin `fetch` works fine.

1. Open the tournament's **Matches** tab and click **Completed**.
2. Open DevTools (`Cmd-Opt-J` on a Mac) and switch to the Console.
3. Paste the whole of `tools/collector.js` and press Enter.

It scrolls until every match has loaded, fetches each one, and downloads
`rcb-scorecards.tsv`. Progress prints as it goes.

If the download is blocked (Chrome refuses more than one automatic download per
page), the data is still there — run this in the same console:

```js
copy(window.__rcb.text)
```

and paste into `league-raw/scorecards.tsv` yourself.

## 2. Install and rebuild

```bash
python3 tools/sync.py
```

It takes the newest `rcb-scorecards.tsv` from `~/Downloads`, checks it, copies
it in, and rebuilds every page and `facts.json`. Then commit and push.

`sync.py` refuses a file that has fewer matches than the one already installed,
because that means the collector was interrupted and quietly replacing good data
with a partial scrape is the mistake you would not notice for weeks. Use
`--force` if you really do mean it; it lists what it is about to drop first.

## What is in the file

Tab-separated. Batting rows have 13 fields, bowling rows 16:

```
B  <match> <inning> <battingTeam>  <player> runs  balls   4s 6s SR   hand howOut     playerId
W  <match> <inning> <bowlingTeam>  <player> overs maidens runs wkts dots 4s 6s wides noballs econ playerId
```

Currently 86 matches: **1,574 batting innings and 1,030 bowling spells**, 562
players, 30 teams.

## What this data is

Each match page embeds `scoreCardData` — both innings, in full. So this is the
**real scorecard**, and the stats built from it are real season figures:
averages, strike rates and economies mean what they normally mean.

Two things it is not. It is not the three-best-performances summary that also
sits on the page (that is a highlight reel and flatters everyone). And it is not
the tournament's own leaderboard, which is behind CricHeroes PRO — we never see
it, and do not need to.

The one thing to watch is **sample size**, not honesty: a strike rate off two
innings is noise. Team tables rank by runs and wickets before rate for exactly
that reason, and every row carries its innings count.

The last field of every row is CricHeroes' `player_id`, and **that is the key to
aggregate on, never the name**. In the matches where someone captained or kept
wicket their name comes through as `Kushal Reddy  (c)` or `Santosh Natarajan
(wk)`, so keying on the name splits one player into two part-records. It did:
66 names, 61 real players, each with their runs divided between two rows.

Worth knowing about this competition: there are **no LBW dismissals at all**
(these are tennis-ball matches), and **76% of dismissals are caught**. Plans
should be about catching, not about trapping people in front.

## Please keep the request rate where it is

`collector.js` runs 3 requests at a time with a 300ms gap. That was measured: six
at once had **a quarter of requests come back 429**, three with a gap had none.
It is somebody's small company being polite to us.
