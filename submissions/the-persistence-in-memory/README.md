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

A PMLL-style short-term silo of hashed 64×64 frames and action outcomes. Prefers novel frame-changing moves, clicks connected-component centroids, tracks a keyboard sprite by frame-diff, and replays JSONL level-up recipes on the next card. Sequential REST play against `three.arcprize.org` with HTTP 429 backoff. Same policy on all 25 public games. No LLM. No per-game hardcoded solutions (recipes are from this agent's own prior public cards).

## Scorecards

ARC-AGI-3 scores are pulled from the card. `submission.yaml` has `scorecard_url` only — **no numeric `score` field**.

| Version | Scorecard | Mode | Public set |
|---|---|---|---|
| 1.0 | https://arcprize.org/scorecards/fa62e88d-607e-402d-91d4-ca61ad597cab | `competition_mode: true` | 25/25 environments, 3/183 levels, 3887 actions (VC33 × 2, R11L × 1) |
| 1.1 | https://arcprize.org/scorecards/6424f517-8080-4c22-8039-accb5bf5877e | `competition_mode: true` | 25/25 environments, 2/183 levels, 3482 actions (VC33 × 1, R11L × 1) |
| 1.3 | https://arcprize.org/scorecards/f7501944-7f70-4050-89af-936a040a65e2 | `competition_mode: true` | 25/25, 2/183, 3418 actions (LP85 × 1, R11L × 1). First JSONL loop. |
| 1.4 | https://arcprize.org/scorecards/660fa699-0f88-4c5d-9e5e-55d132e715d7 | `competition_mode: true` | 25/25, 1/183, 1913 actions (LP85 L1 in 5 actions) |
| **1.5** | https://arcprize.org/scorecards/cfeeae13-dce8-457e-be23-a57725eeac91 | `competition_mode: true` | **25/25, 3/183, 2138 actions — strongest card. VC33 L1 in 11, LP85 L1 in 5, R11L L1 in 118.** |

v1.2 (systematic no-shuffle clicks) scored 0.0 and is omitted from `submission.yaml`; it is documented in the write-up as a negative ablation.

All cards used `POST /api/scorecard/open` with `competition_mode: true` as required by the [Competition Mode docs](https://docs.arcprize.org/toolkit/competition_mode) for the unverified / community path. **v1.5 is the strongest closed card.**

Related community PR for a second method (World Model Agent): [#52](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/pull/52).
