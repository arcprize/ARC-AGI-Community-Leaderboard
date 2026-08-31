# the persistence in memory

Competition-mode ARC-AGI-3 public-set agent, submitted per
[CONTRIBUTING.md](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/blob/main/CONTRIBUTING.md)
and [Competition Mode](https://docs.arcprize.org/toolkit/competition_mode).

- **Directory:** `submissions/the-persistence-in-memory/`
- **Code:** [drQedwards/pmll](https://github.com/drQedwards/pmll) — `lattice/scripts/persistence_in_memory.py` ([pmll#2 merged](https://github.com/drQedwards/pmll/pull/2))
- **Write-up:** [docs/ARC-AGI3-PERSISTENCE.md](https://github.com/drQedwards/pmll/blob/main/docs/ARC-AGI3-PERSISTENCE.md)
- **Display name:** the persistence in memory
- **Author:** Josef K. Edwards (Independent)

## Method

A PMLL-style short-term silo of hashed 64×64 frames and action outcomes. Prefers novel frame-changing moves, clicks connected-component centroids, tracks a keyboard sprite by frame-diff, and replays sequences that previously advanced a level. Sequential REST play against `three.arcprize.org` with HTTP 429 backoff. Same policy on all 25 public games. No LLM. No per-game hardcoded solutions.

## Scorecards

ARC-AGI-3 scores are pulled from the card. `submission.yaml` has `scorecard_url` only — **no numeric `score` field**.

| Version | Scorecard | Mode | Public set |
|---|---|---|---|
| 1.0 | https://arcprize.org/scorecards/fa62e88d-607e-402d-91d4-ca61ad597cab | `competition_mode: true` | 25/25 environments, 3/183 levels, 3887 actions (VC33 × 2, R11L × 1) |
| 1.1 | https://arcprize.org/scorecards/6424f517-8080-4c22-8039-accb5bf5877e | `competition_mode: true` | Click-first + warm silo from 1.0 after pmll#2 |

Both cards used `POST /api/scorecard/open` with `competition_mode: true` as required by the [Competition Mode docs](https://docs.arcprize.org/toolkit/competition_mode) for the unverified / community path.
