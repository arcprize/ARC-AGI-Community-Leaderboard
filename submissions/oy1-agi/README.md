# OY1 AGI

OY1 AGI is an observation-driven ARC-AGI-3 controller that couples visual history
and per-game memory with short, prediction-checked action batches. One live
Competition Mode run scored **100.00%**, solving **25/25 public games and
183/183 levels**, at an inference cost of **$415.37**.

[Source](https://github.com/OYLabsAI/arc-agi-3-api-harness) ·
[Scorecard](https://arcprize.org/scorecards/75d9c8e7-ade9-4a8f-a747-6acbea51bb1b) ·
[Reproduction](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/0c7848dafeb4d7969279b5f193af71112404309a/docs/reproduction.md)

## Method

1. **Observe and retrieve.** The model sees the current screenshot and an exact
   hexadecimal pixel grid. Earlier observations enter retained text history as
   exact grids. The `inspect` tool can revisit a recorded observation, an
   animation frame or a crop; `history` retrieves recorded transitions and notes.
2. **Record hypotheses.** The `remember` tool stores per-game notes with
   hypothesis, supported or refuted labels. A supported note must cite valid
   observed transition indices. The harness validates those references; it does
   not prove the claim itself. No memory is imported from another game or attempt.
3. **Predict and act.** A single action can explore without a prediction.
   Multi-action batches contain at most eight actions and require a prediction
   for each step: selected pixels, game state or completed-level count. The
   runner checks the returned observation after every action and interrupts on
   a mismatch, no observable change, a level transition or a terminal state.
   The model then receives the outcome before choosing its next tool call.
4. **Maintain continuity.** API9 retains provider reasoning items and uses up to
   four rolling text-cache boundaries before the current screenshot. Bounded
   compaction restores the latest exact observation afterward. Compaction is
   lossy; full observations remain in the per-game store for inspection, rather
   than being guaranteed to remain in model context indefinitely.

The same prompt, tools and provider configuration serve all selected games.
The model's interface exposes observations and permitted actions; it provides no
shell, browser, arbitrary Python execution, game source, human action baselines
or previous-run solutions. Cost reservations are enforced by the harness.

Implementation: [runner and action checks](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/0c7848dafeb4d7969279b5f193af71112404309a/harness/arc_harness/runner.py),
[observation store and memory](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/0c7848dafeb4d7969279b5f193af71112404309a/harness/arc_harness/store.py),
[provider context](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/0c7848dafeb4d7969279b5f193af71112404309a/harness/arc_harness/api_provider.py).

## What the completed run used

Aggregate counts from the original per-game event journals for run
`20260909T110238Z-ce055081` are shown below. Requested and dispatched tool counts
agree. These are tool calls, not individual environment actions or API charges.

| Tool | Calls |
|---|---:|
| `act` | 1,436 |
| `remember` | 214 |
| `inspect` | 67 |
| `history` | 11 |
| `plan` | 0 |
| `stop` | 0 |

The optional `plan` tool searches paths through already observed transitions;
**it was never called in this run**. We do not attribute the score to that
planner. The 1,728 decision calls plus 45 compaction operations account for the
1,773 recorded API operations; the runner executed 6,732 environment actions.

## Evaluation and scope

The run completed on 2026-09-09 using OpenAI gpt-6-astra with high reasoning
effort and Standard service. The unrounded successful-run inference cost is
$415.367496. Actions were chosen during the live Competition Mode run, without
replaying a precomputed action trace.

The public games were used during development. Earlier pilots and a full run
stopped by its budget are disclosed in the [attempt history](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/0c7848dafeb4d7969279b5f193af71112404309a/docs/method.md#attempt-history);
scores from attempts were not combined. This result does not establish unseen-game
performance or ARC Prize verification. No controlled ablation establishes which
component caused the score or an advantage over another harness.

The public release preserves all 74 evaluated source files. Its manifest version
is `0.3.8+api9`; the preserved packaging metadata still says `0.3.6+api7`, a
disclosed metadata inconsistency. The reproduction wrapper separately passed
231 tests and a synthetic Linux fixture with zero API operations.

Orca Labs sp. z o.o. / OYLabsAI. Apache-2.0 source license, with separate
dependency notices in the source repository.
