# Retrodict

Retrodict is an LLM agent for ARC-AGI-3 that solves every level of all 25 public games with a mean RHAE of 99.86% on an official competition-mode scorecard, at a total API-list-price cost of $654.34. Full write-up, code, and per-game cost tables: https://github.com/ryanbbrown/Retrodict

Every frame the game returns is logged to a file, and hypotheses about game mechanics must be tested in python against that recorded history (retrodiction) before earning live actions. Committed action plans carry per-step board predictions the runner verifies, and a curated playbook memory survives context resets.

## Versions

- **2.0** (2026-07-19): GPT-5.6 Sol at `max` reasoning effort, with a harness-enforced escalation ladder for stuck levels. 99.86% mean RHAE, 25/25 games solved, $654.34. [Scorecard](https://arcprize.org/scorecards/9c403765-db5b-40b1-beab-6fa3f40119b0)
- **1.0** (2026-07-16): GPT-5.6 Sol at `high` reasoning effort. 84.52% mean RHAE, 21/25 games solved, $418.71. [Scorecard](https://arcprize.org/scorecards/8d734689-3eb9-4dee-b0ce-d822d76e0689). Details archived in the repo at [docs/archive](https://github.com/ryanbbrown/Retrodict/blob/main/docs/archive/2026-07-14-gpt-5.6-sol-high.md).

## How the scorecard was produced

The runs were played on a local runner (games execute in-process from downloaded environment files). To produce the official scorecard, each run's recorded actions were replayed through the ARC-AGI-3 API on a competition-mode card; for version 2.0, all 25 games re-executed exactly. This was done because the games were run with intermittent internet access and would have tripped the server's idle timeout (a live session closes after roughly 15 minutes without an action, and a max-effort run regularly thinks longer than that between moves). Details in the repo's [Validity section](https://github.com/ryanbbrown/Retrodict#validity).

Every run's complete trace (logs, transcripts, playbook, per-request token usage) is downloadable from the repo's [releases](https://github.com/ryanbbrown/Retrodict/releases) for independent verification.
