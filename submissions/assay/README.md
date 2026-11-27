# ASSAY on ARC-AGI-3

## How the scorecard for version 1.0-rc1 was made

Claude Opus 5 played each of the 25 public games once, locally, with ASSAY. The run kept a
journal of every action but did not record scorecard ids. On 2026-08-24 the recorded action
sequences were sent again, unchanged, to the ARC API in one scorecard session:
[702ccd4f](https://arcprize.org/scorecards/702ccd4f-df1f-4118-bc8b-d79d3f4a1a32).

- All 25 replays reproduced their recorded outcome: same final state, levels and action count.
- The card reads 96.54%, 177 of 183 levels, 24 of 25 environments, 8,157 actions. This matches
  the score we computed offline from the journals, game by game.
- No model runs during a replay. The card confirms what the action sequence achieves, not live
  reasoning. Its wall-clock (65 minutes) is replay time; the agent took about 37 hours.

Provenance and per-game receipts:
[SCORECARDS.md](https://github.com/arjmandi/assay/blob/main/bench/arcagi/SCORECARDS.md),
[consolidated_replay_702ccd4f.json](https://github.com/arjmandi/assay/blob/main/bench/arcagi/consolidated_replay_702ccd4f.json).
Journals for every game: [evidence/arcagi/](https://github.com/arjmandi/assay/tree/main/evidence/arcagi).

## How the scorecard for version 1.5.1 was made

A fresh live run on 2026-11-27, in Competition Mode: Claude Sonnet 5.5 with ASSAY 1.5.1
played all 25 public games, one run per game, on one scorecard:
[3e659b9a](https://arcprize.org/scorecards/3e659b9a-7957-49db-b164-93a76e27134a).
The model was in the loop for every action. The agent's prompt and constitution are the
1.5.1 release unchanged; the only changes are in the runner, so that all games share one
competition scorecard.

The card reads 95.19%: 25 of 25 environments, 183 of 183 levels, 11,844 actions. The run
started at 01:15 CET and the card was closed at 05:17 CET; the agent played for 13.6 hours
in all, at most six games at a time.

Journals, transcripts and the agent's notes for every game:
[evidence/arcagi-sonnet55-competition/](https://github.com/arjmandi/assay/tree/main/evidence/arcagi-sonnet55-competition).

Project website: https://arjmandi.github.io/assay/. Paper: https://zenodo.org/records/23685371.
