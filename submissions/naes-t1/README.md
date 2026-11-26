# NAES-T1

NAES-T1 is a 324,096-weight ternary policy network by STARGA, Inc. It plays ARC-AGI-3 games from the rendered 64 x 64 frame: one forward pass per move, closed loop, frame in, move out. Its inference is integer-only and is written in MIND, a public deterministic compiler.

Code: <https://github.com/star-ga/naes-t1> (Apache-2.0). Article: <https://star.ga/research/naes-t1>. Live demo: <https://mindlang.dev/demo/naes-t1/>. Model: <https://huggingface.co/star-ga/naes-t1>. Kaggle: <https://www.kaggle.com/code/cputer/naes-t1-arc-agi-3>. Video: <https://youtu.be/gFOnDSJ8E2g>. Paper: submitted to arXiv; we add the link here when arXiv lists it. STARGA: <https://star.ga>. MIND: <https://mindlang.dev> (compiler source: <https://github.com/star-ga/mind>).

## Determinism

The final run is 5,499 decisions. Their decision stream has the SHA-256 `4d2d98f711a1209eace8f3841952e39d4d75870d48079c3175b361bba9746396`. The check against the final-run fixture prints MATCH 5499/5499 on every substrate measured: the x86-64 CPU build, the NVIDIA RTX PRO 6000 Blackwell Server Edition and the Google Cloud TPU v5e. The arithmetic is integer only, so no floating-point rounding enters a decision. Speed is the supporting line (see the repository README).

## Result

Public demo set: 100.00%, 183/183 levels, 25/25 games, 5,499 actions (live Competition Mode run through the ARC Prize API on the public demo set). Measured by STARGA, not yet verified by ARC Prize. Scorecard: <https://arcprize.org/scorecards/46dc8e53-0718-4182-84a9-88ffe31e282e>. Scorecard recorded on 2026-11-19 (UTC). The release executable gives the same 5,499 decisions (decision-stream digest `4d2d98f711a1209eace8f3841952e39d4d75870d48079c3175b361bba9746396`, `verify` MATCH 5499/5499).

MMAE (Machine-Minimum Action Efficiency) scores a won level by (floor / actions)^2 and a lost level by 0. The floor is the proven machine minimum: the minimum action count that wins the level. All 183 level floors are proven; 2 of them (wa30 levels 8 and 9) by empirical proof. NAES-T1 plays every level at its floor: MMAE 1.000. Why a new measure: what if a game has never been played by people, such as a simulated or newly generated game? The ARC-AGI-3 score compares an agent with a human baseline, so it cannot score that game. MMAE needs no human baseline: it scores any game whose floors are proven.

## How it plays

- Pixels only. It sees only the rendered 64 x 64 frame. No game source code, no internal game state, no level data while playing.
- No game ids. No game, title, level or step number is an input or a switch. Its inputs are the current frame, the previous frame, its own previous action and click cell, and how many times in a row it repeated that action and click cell.
- No stored solutions. The weight file holds weights, scales and biases only: no action lists, no recorded moves, no routes, no click lists.
- One play per game. No copying, saving or rewinding a game. RESET only to continue after GAME_OVER. Every action counts.
- The `play` and `serve` commands read only the weight file and the frames of the current game.

The repository also holds evidence that the player does not read: the floor certificates (each with a replayable winning route, the upper-bound part of a floor proof), the per-game records of the run, and the verification fixture (the 5,499 decision contexts of the final run with their expected decisions, used only by `verify`).

## The three bars

**General-purpose.** NAES-T1 was trained on the mechanics of these 25 games, so the score is not a result on games with unseen mechanics. No semi-private or private game was used for training or play. What does not depend on the game: one network plays every game through the same interface, from pixels only, with no game identifier as an input.

**Open system.** The code that produces every result is public: the MIND program (`src/mind/`), the weights (`model/naes_t1.bin`), the build and check commands, and the public MIND compiler. The open CPU path is the complete system and reproduces every result; GPU inference is OPTIONAL through STARGA's commercial, protected MIND backend and NOT REQUIRED for any result. MIND is a public compiler. The GPU and TPU binaries are protected: their kernel technology is part of STARGA's commercial MIND backends. The CPU build is open source. The GPU and TPU builds are optional. They are STARGA's commercial MIND backends, so their binaries are protected. The CPU build of the MIND program is the open-source release. Anyone who runs a GPU or TPU binary can check its decisions against the CPU build. The results cover the 25 public ARC-AGI-3 demo games and their 183 levels. The training program is not part of this release. Measured by STARGA, not yet verified by ARC Prize.

**Novel contribution.**
1. One decision stream on the x86-64 CPU, the RTX PRO 6000 and the Google Cloud TPU v5e, from one MIND program with integer-only arithmetic.
2. MMAE: a score against the proven machine minimum instead of a human baseline, with a published floor collection and its proofs for all 183 levels.
3. A 329 KB ternary pixel policy: every weight is -1, 0 or +1 times one scale per channel.

## Reproduce

The repository README gives the commands: the build of the CPU executable with the pinned MIND compiler, the `verify` check (MATCH 5499/5499 and the decision-stream digest), the `selftest`, and offline play of the 25 games through the local toolkit with the same action counts.

## Cost

Retail CPU cost of one full 25-game play: US$0.01. The `cost` field is this value, priced at the public on-demand CPU tariff recorded in the repository file `release_evidence/cost/retail_tariff.json`. It does not count development, training or the floor proofs.
