# phase-data

Over-by-over scores for a 40-match sample, used by `tools/phases.py` to build
sections 07-09 of the report.

## `<matchid>.json`

One file per match. Each innings holds `overs` as
`[over_number, runs, wickets, bowler_type_or_null]`.

Collected from the CricHeroes **commentary** tab (the free one), then reconciled
against the match's known final total. 76 of 79 innings matched exactly; the
other three are within a few runs and are marked in the git history.

The 40 matches were chosen to span the full range of totals (38 to 195), both
batting-first and chasing wins, and to cover all 30 teams at least twice.

`bowler_type` is only present for about a quarter of overs, because CricHeroes
shows it in an inline player card that does not appear for every bowler. That is
too sparse to support a pace-vs-spin recommendation, so the report does not make
one.

## `selection.json` / `select.py`

The sampling script and its output - which 40 matches were picked and why.

## `_weather_raw.json` / `_weather_by_date.json`

Hourly weather for the season from the Open-Meteo public archive, and the
per-match-day daytime averages derived from it. Regenerate with:

```bash
curl -s "https://archive-api.open-meteo.com/v1/archive?latitude=43.85&longitude=-79.02&start_date=2025-09-06&end_date=2025-10-12&hourly=temperature_2m,windspeed_10m,winddirection_10m,precipitation&timezone=America%2FToronto" -o phase-data/_weather_raw.json
```

Match start times are not in our fixture data, so these are day-level readings
averaged over 07:00-18:00, not per-match conditions.

## Adding matches

Drop a new `<matchid>.json` in this directory in the same shape and rerun
`python3 tools/build.py`. Innings shorter than 15 overs are automatically
excluded from phase averages (they have no comparable death phase).
