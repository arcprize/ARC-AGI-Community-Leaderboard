# OY1 AGI

OY1 lets a model revisit exact observations and check its predictions before
continuing an action sequence. It uses the same prompt and tools for every
ARC-AGI-3 game, with memory starting fresh each time.

[Source](https://github.com/OYLabsAI/arc-agi-3-api-harness) ·
[Scorecard](https://arcprize.org/scorecards/75d9c8e7-ade9-4a8f-a747-6acbea51bb1b) ·
[Reproduction](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/main/docs/reproduction.md)

## The idea

A model can lose an earlier visual detail or continue acting after its
expectation stops matching the game. OY1 gives it three tools for that problem:

- **Retrieve the observation.** `inspect` returns exact pixel grids from earlier
  observations, including animation frames and crops. `history` retrieves
  transitions and notes.
- **Keep claims tied to observations.** `remember` stores hypotheses and supported
  or refuted notes. A supported note must cite existing transition indices;
  this checks the references, not whether the claim is true.
- **Check a sequence as it runs.** A batch can contain up to eight actions, each
  with a prediction about selected pixels, game state or completed levels. The
  runner checks after each action and stops on a mismatch, no observable change,
  a level transition or a terminal state. Single actions can explore without
  a prediction.

For example, suppose the model requests three moves and predicts the player's
pixel position after each one. If the first move produces a different position,
OY1 returns that observation without executing the other two moves. The model
can inspect the history and revise its next action. This illustrates the control
flow; it is not an excerpt from the benchmark run.

The contribution proposed for review is this combination of exact visual recall,
evidence-linked notes and interrupted action batches. History and hypothesis
checking also appear in other agents; we do not claim those ideas individually
as new. [Related methods and scope](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/main/docs/method.md#contribution-and-generality).

The provider adapter retains reasoning items and caches text history before the
current screenshot. Compaction is lossy; full observations remain available in
the per-game store. The model has no shell, game source or previous-run solutions.
The harness enforces the budget. See the [runner](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/0c7848dafeb4d7969279b5f193af71112404309a/harness/arc_harness/runner.py),
[store](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/0c7848dafeb4d7969279b5f193af71112404309a/harness/arc_harness/store.py) and
[provider adapter](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/0c7848dafeb4d7969279b5f193af71112404309a/harness/arc_harness/api_provider.py).

## Evidence and limits

One live Competition Mode run on 9 September 2026 solved **25/25 public games
and 183/183 levels**, with a **100.0 raw public score** and **$415.37 inference
cost**, using OpenAI gpt-6-astra, high reasoning effort and Standard service.
This is the completed run's inference cost, not total development spending.

The public games were used during development. This is not an unseen-game result
or ARC Prize verification, and no controlled comparison establishes a cost
advantage or which component caused the result. The optional `plan` tool was
never called in this run. The reproduction wrapper's 231 tests and synthetic
fixture check software behavior, not unfamiliar-game performance.

[Per-game results and accounting](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/main/docs/results.md) ·
[Version discrepancy and release status](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/main/docs/compliance.md)

## Proposed follow-up evaluation

The [proposed evaluation protocol](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/main/docs/evaluation-plan.md)
freezes the harness before selecting unfamiliar games, uses a matched baseline
and declares repeat counts and budgets in advance. It has not been run; the
dataset, baseline and budget remain to be chosen.

Orca Labs sp. z o.o. / OYLabsAI. Apache-2.0 source with separate dependency notices.
