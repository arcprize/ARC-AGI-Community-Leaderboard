# Retrodict

Retrodict is an LLM agent for ARC-AGI-3 that completes 21/25 public games with a mean RHAE of 84.52% on an official competition-mode scorecard, at a total cost of $418.71. Full write-up, code, and per-game cost tables: https://github.com/ryanbbrown/Retrodict

Every frame the game returns is logged to a file, and hypotheses about game mechanics must be tested in python against that recorded history (retrodiction) before earning live actions. Committed action plans carry per-step board predictions the runner verifies, and a curated playbook memory survives context resets.

## How the scorecard was produced

The runs were played on a local runner (games execute in-process from downloaded environment files). To produce the official scorecard, each run's recorded actions were replayed through the ARC-AGI-3 API on a competition-mode card; 24 of the 25 games re-executed exactly.

The exception is lf52, which randomizes its starting positions and cannot be replayed; it was played live on the scorecard, and the live attempt scored worse than the original local run (16.30% vs 27.27% RHAE). Details in the repo's [Validity section](https://github.com/ryanbbrown/Retrodict#validity).

Every run's complete trace (logs, transcripts, playbook, per-request token usage) is downloadable from the repo's releases for independent verification.
