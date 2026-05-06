# edmonddantesj ClaudeAgent

## Submission positioning

This is a customized ARC-AGI-3 ClaudeAgent harness built on top of the ARC Prize reference agent repository. It combines source inspection, replay validation, and environment-specific solver modules. The submission should be read as a reproducible community evidence entry, not as a claim of ARC Prize independent verification.

## Current public evidence bundle

Version `0.3` reports a single Competition Mode scorecard covering nine solved ARC-AGI-3 public environments:

- Scorecard: https://arcprize.org/scorecards/0684f4ad-a863-4a5d-9895-59fc31d4033c
- Raw scorecard host equivalent: https://three.arcprize.org/scorecards/0684f4ad-a863-4a5d-9895-59fc31d4033c
- Environments completed: 9 / 9 in the submitted bundle
- Levels completed: 63 / 63 in the submitted bundle
- Total actions: 2135
- Resets: 0

Solved environments in this bundle:

- `sb26-7fbdac44`
- `ft09-0d8bbf25`
- `cd82-fb555c5d`
- `lp85-305b61c3`
- `tr87-cd924810`
- `wa30-ee6fef47`
- `ls20-9607627b`
- `r11l-495a7899`
- `tn36-ef4dde99`

## Earlier LS20 evidence

Version `0.1` was the initial LS20-focused submission:

- Scorecard: https://arcprize.org/scorecards/6d4fc6dd-bc19-4a16-9357-13b7b9789970
- Raw scorecard host equivalent: https://three.arcprize.org/scorecards/6d4fc6dd-bc19-4a16-9357-13b7b9789970
- Reported result at the time: LS20 level 5 progress, 2000 actions

## Method notes

The customized `agents/claude_agent.py` implementation includes a mix of targeted solver modules and replay-safe action plans. Examples of implemented behavior include:

- source-aware LS20 parsing from `environment_files/ls20/.../ls20.py`
- compound-state A* / presolve logic for LS20 state variables
- enemy bumper push resolution and second-pass tile effects
- energy tile consumption / reset handling
- dynamic transform-zone detection
- verified per-level replay slices for WA30 without `ACTION0`/RESET emission
- deterministic solvers or replay plans for the nine solved public environments listed above

## Reproducibility notes

The scorecards were generated with ARC-AGI-3 Competition Mode. The public code repository linked in `submission.yaml` should include the modified agent code and enough notes to reproduce the claimed scorecard behavior.
