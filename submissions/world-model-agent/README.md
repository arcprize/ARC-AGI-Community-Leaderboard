# World Model Agent

Community Leaderboard entry for a **structured world-model** agent on ARC-AGI-3.

## Method (short)

1. **Deterministic WorldModel** — each frame is parsed into player / door / rotator / energy positions, visited cells, and confirmed blocked moves (in-process memory; no LLM for perception).
2. **Exploration phase** — first N actions after a full reset systematically sweep the play area so the model is populated before planning.
3. **LLM planner with injected summary** — `WorldModel.summary` is appended to the system prompt every turn so the model plans over structured state instead of re-reading the raw grid.
4. **Same harness** — runs on the official ARC-AGI-3 agents stack (`uv run main.py --agent=worldmodelagent --game=...`).

## Public code

- Repo: https://github.com/drQedwards/ARC-AGI-3-Agents  
- Primary agent: `agents/templates/world_model_agent.py` (`--agent=worldmodelagent`)  
- Related: `agents/templates/lot_agent.py` (Language of Thought), `arc_agi3_pmll_agent.py` (PMLL memory MCP)

## Scorecard

Competition-mode scorecard:  
https://arcprize.org/scorecards/a4618274-e508-43d9-92f8-0108dbae9e39

## Related JSONL loop (same author, second method)

[PR #51](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/pull/51) is **the persistence in memory**, a $0 no-LLM PMLL silo agent. Compact level-up JSONL: https://github.com/drQedwards/pmll/blob/main/docs/arc-agi3-levelups.jsonl — write-up: https://github.com/drQedwards/pmll/blob/main/docs/ARC-AGI3-PERSISTENCE.md

Strongest public competition-mode persistence card (v1.5): https://arcprize.org/scorecards/cfeeae13-dce8-457e-be23-a57725eeac91 (3/183 levels; LP85 L1 in 5 actions, VC33 L1 in 11, R11L L1 in 118).

## Run

```bash
git clone https://github.com/drQedwards/ARC-AGI-3-Agents.git
cd ARC-AGI-3-Agents
cp .env.example .env   # set ARC_API_KEY / model keys
uv sync
uv run main.py --agent=worldmodelagent --game=ls20
```
