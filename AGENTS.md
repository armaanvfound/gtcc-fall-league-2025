# GTCC League dashboard — the map for any agent

Public site for Royal Challenger Blaster (RCB), GTCC Fall League 2026. Lives on
GitHub Pages from this repo's `main`; every push publishes. The captain's
standing instruction is one word — **"sync"** — and this file is what makes that
word mean the same thing in a session that has never seen the conversation.

`CLAUDE.md` in this repo is a symlink to this file.

## What "sync" does, in order

1. **Harvest** every completed 2026 league match through the user's own Chrome
   (claude-in-chrome). Paste `tools/collect2026.js` or drive the same fetches
   from a tab on cricheroes.com. Fetches work from a background tab; only
   rendering does not. Tournament id **2167460** (share link
   chshare.link/tournament/54auYA). Concurrency 2–3 with a ~500 ms gap — faster
   draws 429s.
2. **Install + rebuild**: `python3 tools/sync2026.py` — takes the newest
   `rcb-results-2026*.tsv` in `~/Downloads` BY MODIFIED TIME (browsers rename
   repeats to "(1).tsv"), validates every row shape including the I-row
   all-out flag, refuses a harvest with fewer matches than installed, rebuilds
   all pages + `facts.json`, prints Group 5 as a sanity check.
3. **If a new RCB match is in the harvest**: add `our-matches/<id>.json`. Its
   scorecard half comes from the harvest; its **phase splits need the
   commentary rendered** — Chrome in the FOREGROUND for ~30 s. Use
   `tools/capture_commentary.js` (run once per innings, then `__rcb.emit(15)`),
   reconcile every line against the scorecard, set `allOut`, write the file.
   Ask the user to bring Chrome forward; do everything else first. The pipeline
   tolerates a match without phases (it counts in the record/NRR/careers and is
   labelled as awaiting its split) so a sync never blocks on this.
4. `git add -A && git commit && git push`, wait for Pages, then
   `python3 tools/eval_assistant.py` against the live chatbot. **A sync is not
   done until the eval passes.** Report the Group 5 table and eval result.

One file — `league-raw/results-2026.tsv` — feeds results, the points table,
leaderboards, ground cards, every opponent's "This season" block, our record
when we play, and the chatbot's fact pack. Nothing needs enabling per team.

## Layout (four pages, one job each)

- `index.html` **Match plan** — next match strip, fixtures with an evidence
  chain (our head-to-head → their 2026 results → 2025 profile → other-format
  form), and the opponent **dossier** dropdown: toss/target, the ground (both
  seasons), this season's form + players, 2025 phase plan/profile, 2025 season
  tiles/reads/log, players. The dossier must hold everything about an
  opponent; nobody should need another tab on match day.
- `season.html` **The season** — schedule, computed points table, results,
  grounds (2026 beside 2025), leaderboards.
- `form.html` **Our form** — league record (friendlies excluded), every match
  ball by ball, phase habits, player careers.
- `league.html` **2025 intel** — last season read in full; opens with a banner
  saying it is the evidence base, not the live season.

Build: `tools/build.py` slices `tools/template.html` per page (PAGES config:
sections by id, JS blocks by their `/* name */` comment, payload keys). Every
page is pure ASCII, self-contained, no fetch at read time.

## Conventions that were each a bug once — keep them

- **Record and NRR are league-only.** The FERAL games were pre-season
  friendlies; they feed phase habits (labelled) but never the record.
- **NRR all-out rule**: a side bowled out counts its full quota of overs.
  Use CricHeroes' `is_allout` flag, never `wkts >= 10` — 10-a-side teams are all
  out at 9 down, and the inference once handed NRR to the wrong team.
- **Key players on `player_id`, never name.** `Kushal Reddy  (c)` and
  `Kushal Reddy` are one person; keying on name split 61 players.
- **Team aliases** in `tools/results2026.py` (`Durham Strikers - T15`, `YRICA`,
  `PunjabXI`, `North Stars`, `Feral`...). A missed alias forks a team: the match
  books under a phantom while the roster row stays at played-0. After every
  sync, look for played-0 teams in a group that has results.
- **Ground keys** normalise names; 2025's "Stom Street Park" typo venue is
  merged into Stone Street (weighted). See `tools/grounds2026.py`.
- **Era discipline**: every block wears its year. 2026 says WHO is scoring and
  how much; 2025 owns WHEN in an innings (phase splits exist for 2026 only for
  our own games). Never blend the two into one claim.
- **Chasing averages read low by construction** (a won chase stops at the
  target). Say so wherever one is shown.
- **Small samples hedge themselves** in copy (ground reads, leaderboards).
- **Bowler phase accounting** is bowler-credited: no run-out wickets, no
  bye/leg-bye runs; wides and no-balls are charged. Team phases count all.
- **CricHeroes over numbering**: ball N.0 is the LAST ball of over N.
- **The chatbot never calculates.** `tools/factpack.py` precomputes everything;
  `_prompt` in facts.json holds the rules. Standing toss call is BAT (from
  `tossPolicy`); the assistant quotes decisions the pack has made rather than
  re-deriving them. Markdown is stripped client-side.
- **Fact pack depth**: it holds top-5 per leaderboard and top-4 players per
  team; it must say so ("not in the top five", never "not on the board").

## Tools

`collect2026.js` (season harvest) · `sync2026.py` (install/validate/rebuild) ·
`capture_commentary.js` (our ball-by-ball) · `results2026.py`, `standings2026.py`,
`leaders2026.py`, `opponents2026.py`, `grounds2026.py`, `qualify2026.py` (all
derive from the one TSV) · `ourmatches.py` (our record, phases, careers) ·
`league_players.py` (2025 player stats from `league-raw/scorecards.tsv`) ·
`factpack.py` (chatbot facts) · `eval_assistant.py` (22-question grounding
check) · `collector.js` / `sync.py` (the 2025 archive harvest, rarely needed).

The chatbot proxy is a Cloudflare Worker in `worker/` (DeepSeek, reasoning
off — measured; key is a Worker secret, never in the repo).

## Never

- Never route around Cloudflare (proxies, challenge solving). Reads happen in
  the user's own browser session or not at all.
- Never scrape CricHeroes' PRO/leaderboard pages — we compute our own from the
  harvest, and they are better for it.
- Never write an API key into a file, even when told it is fine.
