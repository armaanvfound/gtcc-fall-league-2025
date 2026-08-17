# GTCC Fall League — match analysis

A single-page, data-driven analysis of the Amiirtham GTCC Fall League, built to be
shared with a team over WhatsApp and updated through the season.

**Live:** <https://armaanvfound.github.io/gtcc-fall-league-2025/>

The page is one self-contained HTML file — no CDN, no fetch, no build step at load
time. It works served from GitHub Pages and equally well opened straight off disk,
online or off.

## Adding matches

1. Open `tools/data.py` and append rows to `RAW`. One row per match:

   ```python
   ("2025-10-12", F, AJAX, 15, "Mavericks", 119, 9, 15.0,
                               "Nizam Royal Knights", 102, 8, 15.0,
                               "Mavericks", "17 runs"),
   ```

   | field | meaning |
   |---|---|
   | `"2025-10-12"` | date, `YYYY-MM-DD` |
   | `F` | round — one of `LG`, `PQF`, `QF`, `SF`, `F` |
   | `AJAX` | ground — use an existing constant or add one at the top of the file |
   | `15` | overs per side |
   | next four | **team batting first**, runs, wickets, overs faced |
   | next four | **team batting second**, runs, wickets, overs faced |
   | last two | winner, and the margin exactly as CricHeroes writes it |

   Overs use cricket notation: `14.3` means fourteen overs and three balls.
   For a walkover, pass `None` for all four score fields on both sides.

2. Rebuild and check the summary it prints:

   ```bash
   python3 tools/build.py
   ```

3. Commit and push. GitHub Pages redeploys in under a minute:

   ```bash
   git add -A && git commit -m "Add round N results" && git push
   ```

To preview before pushing, open `index.html` in a browser — or run
`python3 -m http.server 4173` and visit <http://localhost:4173>.

## How the numbers are computed

- **Score-based analysis uses 15-over matches only.** Two group games were played
  over 12 overs, so their totals are not comparable and are excluded from the
  win-line bands and the scoring averages. They still count in records.
- **Net run rate** charges an all-out innings the full quota, as the competition
  regulations do — not the overs actually faced.
- **Groups** are derived from the fixture list itself: each connected component of
  the league-stage graph is a group, so this keeps working if the format changes.
- **Walkovers** count in win–loss records but not in run rates.

## Provenance

Fixtures, dates, grounds, rounds and overs came from the league fixture
spreadsheet. That export did not include scores or winners, so those were read
from the CricHeroes match list and cross-checked against it: all 88 matches agree
on batting order, overs faced, margin, round and quota, and every margin
reconciles against the two totals with no arithmetic exceptions.

Not included: individual batting and bowling figures, and toss results. The
analysis therefore speaks to *how* to play, not *whom* to pick.

## Layout

```
index.html        generated — do not edit by hand
tools/data.py     the match data. this is the file you edit
tools/stats.py    computes standings, NRR, groups, win-line bands
tools/template.html  page markup, styling and client-side JS
tools/build.py    rebuilds index.html from the above
```
