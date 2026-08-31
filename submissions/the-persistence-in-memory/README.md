# the persistence in memory

Competition-mode ARC-AGI-3 public-set agent. Submitted per [CONTRIBUTING.md](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/blob/main/CONTRIBUTING.md) and [Competition Mode](https://docs.arcprize.org/toolkit/competition_mode).

- **Code:** [drQedwards/pmll](https://github.com/drQedwards/pmll) `lattice/scripts/persistence_in_memory.py` ([PR #2 merged](https://github.com/drQedwards/pmll/pull/2))
- **Write-up:** [docs/ARC-AGI3-PERSISTENCE.md](https://github.com/drQedwards/pmll/blob/main/docs/ARC-AGI3-PERSISTENCE.md)
- **Display name:** the persistence in memory
- **Author:** Josef K. Edwards (Independent)

## Method

A PMLL-style short-term silo of hashed 64×64 frames and action outcomes. Prefers novel frame-changing moves, clicks connected-component centroids, tracks a keyboard sprite by frame-diff, and replays sequences that previously advanced a level. Sequential REST play against `three.arcprize.org` with HTTP 429 backoff. Same policy on all 25 public games. No LLM. No per-game hardcoded solutions.

## Scorecards

ARC-AGI-3 scores are pulled from the card ([CONTRIBUTING.md](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/blob/main/CONTRIBUTING.md)). `submission.yaml` has `scorecard_url` only — no numeric `score` field.

| Version | Card | Mode | Public set |
|---|---|---|---|
| 1.0 | https://arcprize.org/scorecards/fa62e88d-607e-402d-91d4-ca61ad597cab | `competition_mode: true` | 25/25 environments, 3/183 levels |
| 1.1 | https://arcprize.org/scorecards/6424f517-8080-4c22-8039-accb5bf5877e | `competition_mode: true` | in flight; version entry added when closed |

The 1.0 card is the required `scorecard_url` in `submission.yaml` v1.0.
