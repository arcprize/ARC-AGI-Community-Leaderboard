# edmonddantesj ClaudeAgent LS20

## Submission Positioning
This submission should be presented as a custom LS20-focused ARC-AGI-3 agent built on top of the ARC Prize reference repository, not as a plain mirror of upstream.

## Core proof points to surface in the public repo

### 1) Custom solver behavior in `agents/claude_agent.py`
Verified directly from the current code:

- Source-aware parsing of LS20 game source from `environment_files/ls20/.../ls20.py`
- Compound-state A* / presolve logic over:
  - player position
  - shape
  - color index
  - rotation index
  - completed-key mask
  - remaining step counter
  - consumed-energy mask
- Enemy bumper push resolution and second-pass tile effects
- Energy tile consumption / reset handling
- Dynamic transform-zone detection
- Special live handling for dynamic level barrier
- Fallback exploration heuristics including:
  - bootstrap mode
  - align modes
  - anti-loop behavior
  - macro-bank exploration

### 2) Official online scorecard run
- Scorecard URL:
  https://three.arcprize.org/scorecards/6d4fc6dd-bc19-4a16-9357-13b7b9789970

### 3) Reported public result
- Benchmark: ARC-AGI-3
- Set: public
- Score: 53.57
- Levels completed: 5
- Total actions: 2000

## Important note on scorecard visibility
The scorecard URL currently uses the same `three.arcprize.org/scorecards/<uuid>` pattern already present in existing community leaderboard submissions. If public browser access is inconsistent or redirects to the general ARC-AGI-3 page, the repository documentation should still make the run provenance explicit by repeating:

- scorecard id
- result summary
- code location of the custom logic
- method description

## Suggested repo-facing framing
Use wording like:

> This repository started from the ARC Prize ARC-AGI-3-Agents base and was then extended with custom LS20-specific solver logic, online experimentation, and iterative debugging. The reported score corresponds to the custom `claudeagent` implementation documented here.

## Recommended next commit contents
To strengthen the submission before PR:
- add this document to the public repo
- add a short repo README section titled `Community Leaderboard Evidence`
- mention the scorecard id explicitly
- mention that future versions will update as additional levels are cleared
