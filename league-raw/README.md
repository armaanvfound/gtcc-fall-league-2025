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

Tab-separated. Batting rows have 17 fields, bowling rows 20 - the last four on
every row are the competition, so formats are never silently blended:

```
B <match> <inn> <battingTeam> <player> runs balls 4s 6s SR hand howOut playerId  <tourId> <tournament> <overs> <ball>
W <match> <inn> <bowlingTeam> <player> overs maidens runs wkts dots 4s 6s wides noballs econ playerId  <tourId> <tournament> <overs> <ball>
```

Currently **498 matches across seven competitions**, 1,315 players, 93 clubs:

| Matches | Competition | Format |
|---|---|---|
| 110 | GTCC Spring League 2026 | 12-over tennis |
| 90 | Dosa & Biryani House GTCC T20 2025 | 20-over tennis |
| 87 | GTCC Madhuram Summer League 2025 | 12-over tennis |
| 86 | Amiirtham GTCC Fall League 2025 | 15-over tennis |
| 78 | GTCC Summer T12 League 2026 | 12-over tennis |
| 35 | GTCC Hardball T20 League 2025 | 20-over **leather** |
| 12 | EKCT v8 2026 Champions Division | tennis |

## Two aggregation rules that are not optional

**Aggregate on `player_id`, never the name.** CricHeroes appends `(c)` or `(wk)`
in the matches where someone captained or kept wicket, so the same person arrives
under two names. Keying on the name split 61 players into two part-records each.

**Canonicalise the club name.** Clubs re-register every season, so one side
appears as `South Warriors` and `South Warriors 2026`, `Maratha Warriors` and
`Maratha Warriors - GTCC`. Only trailing season decoration is stripped - never a
leading word, because `Royal Punjab` and `United Punjab` are different teams.

## What is deliberately left out of the pooled stats

The **Hardball league is played with a leather ball**. That is a materially
different game and its averages do not belong in the same column as the
tennis-ball leagues, so its rows stay in this file, tagged, but are excluded from
the pooled player figures.

Two competitions were **not collected**: LISA Indoor Cricket and Weekend Cricket
Recreational. Indoor is a different sport, and a check of the small competitions
showed they contain **none** of our 2026 opponents - Hardball and EKCT contain
none either. The big five tennis-ball leagues are where our opponents actually
play.

Also worth knowing: **Lisa Challengers and United Punjab**, two sides in our 2026
group, appear in none of these competitions. We have no data on them at all, and
scraping more of these leagues will not produce any.

## Please keep the request rate where it is

`collector.js` runs 3 requests at a time with a 300ms gap. That was measured: six
at once had **a quarter of requests come back 429**, three with a gap had none.
It is somebody's small company being polite to us.
