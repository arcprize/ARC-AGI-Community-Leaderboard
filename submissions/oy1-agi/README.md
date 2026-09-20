# OY1 AGI

OY1 runs a language model on ARC-AGI-3 games. It stores each game's observations
and gives the model tools to retrieve earlier frames, record notes and check
the outcome of an action sequence. Every game uses the same prompt and tools,
with a fresh history and memory store.

[Code](https://github.com/OYLabsAI/arc-agi-3-api-harness) ·
[Scorecard](https://arcprize.org/scorecards/75d9c8e7-ade9-4a8f-a747-6acbea51bb1b) ·
[Reproduction](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/main/docs/reproduction.md)

## How it works

The model can retrieve an earlier observation as an exact pixel grid, including
animation frames and crops. It can also save notes with references to recorded
transitions. The store checks that those references exist; the model is still
responsible for interpreting them.

For a batch of up to eight actions, the model predicts selected pixels, game
state or completed levels after each step. The runner checks each result and
stops the batch on a mismatch, no observable change, a level transition or a
terminal state. For example, if the first of three moves ends at the wrong
predicted position, the other two moves are cancelled. A single action can
explore without a prediction.

The model receives screenshots and grids, but no shell, game source or stored
solutions. The adapter preserves provider reasoning items and compacts context
when needed. Full observations remain in the per-game store after compaction.
The [method](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/main/docs/method.md)
links these behaviors to the implementation and related work.

## Result

The completed run on 9 September 2026 solved **25/25 public games and all 183
levels** using GPT-6 Astra at high reasoning, for **$415.37 in inference cost**.

On the same game versions and model/reasoning setting, the published Provider
Adapter replays contain **901,970,049 total tokens**. OY1 reports **153,058,391**,
including compaction: **83.03% fewer total tokens**. Cached input is included,
and both completed all 183 levels. The [comparison](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/main/docs/token-comparison.md)
includes replay links, per-game totals, hashes and a reproduction script.

Public games were used during development. This comparison does not establish
performance on unfamiliar games or isolate the effect of individual components.
Token savings also do not translate directly to dollar savings. The optional
planner was not used. The [evaluation plan](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/main/docs/evaluation-plan.md)
sets out the proposed matched comparisons and ablations.

[Run accounting](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/main/docs/results.md) ·
[Release status](https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/main/docs/compliance.md)

Orca Labs sp. z o.o. / OYLabsAI. Apache-2.0, with separate third-party notices.
