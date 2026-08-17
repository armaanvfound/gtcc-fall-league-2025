# phase-data

Over-by-over scores for all 86 played matches, used by `tools/phases.py` to
build sections 07-09 of the report.

## `<matchid>.json`

One file per match. Each innings holds `overs` as
`[over_number, runs, wickets, bowler_type_or_null]`.

Collected from the CricHeroes **commentary** tab (the free one), then reconciled
against the match's known final total. Most innings matched exactly; a handful
that ended mid-over (the batting side all out or the chase won before the last
ball) are short by the last few runs, since a truncated over has no "END OF
OVER" summary line to read the total from - those are still excluded from
phase averages regardless (see below), so the gap doesn't affect any number in
the report.

`bowler_type` is present for roughly 60% of overs - CricHeroes shows it in an
inline player card that appears for most but not all bowlers.

## `selection.json` / `select.py`

The original 40-match sampling script and its output, from before the dataset
was expanded to all 86 played matches. Kept for reference; no longer used by
`tools/phases.py`.

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
