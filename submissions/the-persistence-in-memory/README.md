# the persistence in memory

Competition-mode ARC-AGI-3 public-set agent, submitted per
[CONTRIBUTING.md](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/blob/main/CONTRIBUTING.md)
and [Competition Mode](https://docs.arcprize.org/toolkit/competition_mode).

- **Directory:** `submissions/the-persistence-in-memory/`
- **Code:** [drQedwards/pmll](https://github.com/drQedwards/pmll) — `lattice/scripts/persistence_in_memory.py` ([pmll#2 merged](https://github.com/drQedwards/pmll/pull/2))
- **Write-up:** [docs/ARC-AGI3-PERSISTENCE.md](https://github.com/drQedwards/pmll/blob/main/docs/ARC-AGI3-PERSISTENCE.md)
- **JSONL (level-ups only):** [docs/arc-agi3-levelups.jsonl](https://github.com/drQedwards/pmll/blob/main/docs/arc-agi3-levelups.jsonl)
- **Display name:** the persistence in memory
- **Author:** Josef K. Edwards (Independent)

## Method

A PMLL-style short-term silo of hashed 64×64 frames and action outcomes. Prefers novel frame-changing moves and clicks connected-component centroids. v1.4 and v1.5 are warm-start: they replay ACTION6 level-up clicks ("recipes") from earlier runs first. v1.3 was the first run to write a JSONL log; whether it loaded anything is unknown (see the table below). Sequential REST play against `three.arcprize.org` with HTTP 429 backoff. Same policy on all 25 public games. No LLM.

**Sprite tracking does not work in any submitted version.** The code includes a frame-diff tracker (`moved_centroid`) meant to learn which keyboard action moves the sprite in which direction. It has a bug: every changed cell is appended to both the "lost" and "gained" lists with the same `(x, y)`, so both centroids are identical and the computed movement is always `(0, 0)`. The direction map `silo.moves` therefore stays empty, and the directed-navigation branch (`if silo.moves and ...`) never runs. Keyboard games were played only with the fallback (novelty / shuffled) moves. This is consistent with the cards: every card scores 0 levels on the `keyboard` and `keyboard_click` tags; all completed levels are on `click` games. The bug is present in pmll [`d1a68dc`](https://github.com/drQedwards/pmll/blob/d1a68dc/lattice/scripts/persistence_in_memory.py) and [`4cff3a5`](https://github.com/drQedwards/pmll/blob/4cff3a5/lattice/scripts/persistence_in_memory.py) (and still at `85f70e8`); it is not fixed in the submitted versions.

**Seeded recipes disclosure.** In the v1.5 code (pmll `4cff3a5`), `SEED_RECIPES` hardcodes click coordinates for three games — LP85 (6,33), R11L (36,20) and (36,26), VC33 (61,32) — that are loaded into the silo before play. These were taken from this agent's own earlier runs, not from game source. The other 22 games have no seeded recipe.

## Scorecards

ARC-AGI-3 scores are pulled from the card. `submission.yaml` has `scorecard_url` only — **no numeric `score` field**.

| Version | Scorecard | Mode | Public set |
|---|---|---|---|
| 1.0 | https://arcprize.org/scorecards/fa62e88d-607e-402d-91d4-ca61ad597cab | `competition_mode: true` | 25/25 environments, 3/183 levels, 3887 actions (VC33 × 2, R11L × 1) |
| 1.1 | https://arcprize.org/scorecards/6424f517-8080-4c22-8039-accb5bf5877e | `competition_mode: true` | 25/25 environments, 2/183 levels, 3482 actions (VC33 × 1, R11L × 1) |
| 1.3 | https://arcprize.org/scorecards/f7501944-7f70-4050-89af-936a040a65e2 | `competition_mode: true` | 25/25, 2/183, 3418 actions (LP85 × 1, R11L × 1). First JSONL loop. |
| 1.4 | https://arcprize.org/scorecards/660fa699-0f88-4c5d-9e5e-55d132e715d7 | `competition_mode: true` | 25/25, 1/183, 1913 actions (LP85 L1 in 5 actions) |
| **1.5** | https://arcprize.org/scorecards/cfeeae13-dce8-457e-be23-a57725eeac91 | `competition_mode: true` | **25/25, 3/183, 2138 actions. VC33 L1 in 11, LP85 L1 in 5, R11L L1 in 118.** |

v1.2 (systematic no-shuffle clicks) scored 0.0 and is omitted from `submission.yaml`; it is documented in the write-up as a negative ablation.

All cards used `POST /api/scorecard/open` with `competition_mode: true` as required by the [Competition Mode docs](https://docs.arcprize.org/toolkit/competition_mode). Card metadata below is from `https://arcprize.org/api/v3/scorecards/<id>`. Card times are UTC on 2026-08-31.

## Per-version code and starting memory

"Cold" = the run starts with an empty silo. "Warm-start" = the run loads saved state (recipes / click hits) from earlier runs. All versions also fetch the metadata (score, level count, titles) of a reference scorecard at startup and record it in the card's `source` metadata; the code does not use it to choose actions.

| Version | Card (opened UTC) | Card tag | Code | Starting memory | Label |
|---|---|---|---|---|---|
| 1.0 | `fa62e88d` (21:32) | none | pmll [`d1a68dc`](https://github.com/drQedwards/pmll/blob/d1a68dc/lattice/scripts/persistence_in_memory.py#L409-L415) (committed 21:47 UTC, after the card) | Empty: `silo = Silo()` with no ingest | Cold |
| 1.1 | `6424f517` (21:55) | `v1.1` | Not committed as a separate revision; between `d1a68dc` and `4cff3a5` | Described at the time as "warm silo after pmll#2 merge"; the exact state loaded is not recorded in git | Warm-start (per the original changelog; contents not reconstructable) |
| 1.3 | `f7501944` (22:34) | `v1.1` | Not committed as a separate revision | First run to write a JSONL action log. Whether it ingested anything is not recorded; no earlier JSONL log exists in the repo | Undetermined (see note) |
| 1.4 | `660fa699` (22:45) | `v1.4` | Not committed as a separate revision | JSONL level-up clicks from the v1.3 run (LP85 (6,33), R11L (36,26), per [`levelups.jsonl`](levelups.jsonl)) | Warm-start |
| 1.5 | `cfeeae13` (23:01) | `v1.5` | pmll [`4cff3a5`](https://github.com/drQedwards/pmll/blob/4cff3a5/lattice/scripts/persistence_in_memory.py#L603-L609) (committed 23:09 UTC, after the card) | `ingest_jsonl()` reads all prior local JSONL logs (v1.3, v1.4) and adds `SEED_RECIPES` for LP85, R11L, VC33 | Warm-start |

**How recipes were generated and selected.** `ingest_jsonl()` scans earlier runs' JSONL logs and, whenever `levels_completed` rose after an `ACTION6` click, stores that click's `(x, y)` for that game; the agent tries those recipes first (up to `RECIPE_TRIES = 6`) on each life. There is no other selection step. `SEED_RECIPES` are those same kinds of coordinates written directly into the source. LP85 (6,33) and R11L (36,26) match the v1.3 log. R11L (36,20) first appears in the v1.5 log, and VC33 (61,32) appears in no log before v1.5 (VC33 levels on v1.0/v1.1 predate the JSONL log). The author copied these coordinates in by hand from the agent's own earlier scorecards and did not change any values.

**Why the v1.3 card is tagged `v1.1`.** The card tag comes from a hardcoded list in the script. The v1.3 run evidently still carried the `v1.1` tag string; the exact cause cannot be confirmed because that revision was not committed. The listed version follows the order of runs, not the tag.

**Note on reproducibility.** Only v1.0 (`d1a68dc`) and v1.5 (`4cff3a5`) correspond to committed code, and both were committed after their cards ran, so the committed files are the author's record of that code rather than a verified snapshot. Later pmll commits (`85f70e8`, review fixes) change the script further and are not the submitted code.

Related community PR for a second method (World Model Agent): [#52](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/pull/52).
