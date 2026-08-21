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
`rcb-performances.tsv`. Progress prints as it goes.

If the download is blocked (Chrome refuses more than one automatic download per
page), the data is still there — run this in the same console:

```js
copy(window.__rcb.text)
```

and paste into `league-raw/performances.tsv` yourself.

## 2. Install and rebuild

```bash
python3 tools/sync.py
```

It takes the newest `rcb-performances.tsv` from `~/Downloads`, checks it, copies
it in, and rebuilds every page and `facts.json`. Then commit and push.

`sync.py` refuses a file that has fewer matches than the one already installed,
because that means the collector was interrupted and quietly replacing good data
with a partial scrape is the mistake you would not notice for weeks. Use
`--force` if you really do mean it; it lists what it is about to drop first.

## What is in the file

Tab-separated, one row per standout performance:

```
B  <match>  <inning>  <team>  <player>  runs  balls  4s  6s  strikeRate  isOut   playerId
W  <match>  <inning>  <team>  <player>  overs runs   wkts econ dots      maidens playerId
```

## What this data is, and is not

Each match page publishes its **top three batting and top three bowling
performances**. That is what this collects — 258 of each across 86 matches.

The full scorecard is never sent to the browser, and the tournament's own
leaderboard and stats pages are behind CricHeroes PRO. So this is the deepest
per-player data actually reachable without a subscription.

It is a **threat list, not a set of averages**. A player's quiet matches are not
in here, and players who never had a standout day do not appear at all. Read as
an average it flatters everybody. Every label on the dashboard and every line in
`facts.json` is worded to keep that straight, and the assistant is told the same.

## Please keep the request rate where it is

`collector.js` runs 3 requests at a time with a 300ms gap. That was measured: six
at once had **a quarter of requests come back 429**, three with a gap had none.
It is somebody's small company being polite to us.
