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

## Run

```bash
git clone https://github.com/drQedwards/ARC-AGI-3-Agents.git
cd ARC-AGI-3-Agents
cp .env.example .env   # set ARC_API_KEY / model keys
uv sync
uv run main.py --agent=worldmodelagent --game=ls20
```
