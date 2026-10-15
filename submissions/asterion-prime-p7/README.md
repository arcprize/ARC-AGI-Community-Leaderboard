# Asterion Prime P7

Asterion Prime P7 completed **25/25 public ARC-AGI-3 games and 183/183 levels in 6,781 actions**, with **100.00** on a closed official Competition scorecard. The routes were discovered through iterative LLM research with retained experience, then replayed online. [Code and write-up](https://github.com/uukuguy/asterion/blob/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/README.md) · [Result and accounting](https://github.com/uukuguy/asterion/blob/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/docs/results/arc-agi-3/README.md) · [Replay console](https://asterion-p7-console.vercel.app).

[![Official ARC-AGI-3 score overview and all 25 game results: 100.00, 183 levels, 6,781 actions](https://raw.githubusercontent.com/uukuguy/asterion/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/docs/assets/arc-agi-3/p7-official-scorecard.png)](https://arcprize.org/scorecards/60c10b53-9b8d-4af9-aae7-85f81543198a)

Official overview and all 25 game results. [Full-page screenshot](https://raw.githubusercontent.com/uukuguy/asterion/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/docs/assets/arc-agi-3/p7-official-scorecard-full.png).

P7's contribution is its combination of an LLM-maintained **WorldMap**, persistent IPython hypotheses and search programs, checked short action plans, and selective reuse of experience from successful and failed attempts. The WorldMap records candidate rules, action meanings, goals, unknowns, competing hypotheses, and supporting evidence. The LLM uses it to choose computations or discriminating experiments, writes and revises executable models, and compares their predictions with recorded observations and real action outcomes. The general machinery learns from observations; game-specific programs and saved routes are research outputs rather than supplied answer tables.

The current registered tools are exactly **`ipython`, `p7_workspace`, and `p7_execute_plan`**. Plans bind predictions to the current observation and workspace revision; the broker executes sequentially and stops on mismatch, level boundary, RESET, or termination. Counterexamples guide revision. Later attempts can reuse recorded corrections, artifacts, and program cells, while an independently checked successful prefix can be restored in a new local game. RESET preserves durable experience but clears pending planner authority. Producing code: [prompt](https://github.com/uukuguy/asterion/blob/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/src/asterion/applications/prime/p7/prompt.py), [tool registry](https://github.com/uukuguy/asterion/blob/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/src/asterion/applications/prime/p7/tool_registry.py), [workspace](https://github.com/uukuguy/asterion/blob/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/src/asterion/applications/prime/p7/research.py), [broker](https://github.com/uukuguy/asterion/blob/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/src/asterion/applications/prime/p7/broker.py), [experience](https://github.com/uukuguy/asterion/blob/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/src/asterion/applications/prime/p7/experience.py), and [certificates](https://github.com/uukuguy/asterion/blob/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/src/asterion/applications/prime/p7/solution_certificates.py).

## Version

- **[P7-2026-10-07](https://github.com/uukuguy/asterion/tree/P7-2026-10-07)** (2026-10-07, UTC+8): `gpt-6.1-sol`, Pi `openai-codex`, seed `0`. Official **100.00**, 25/25 games, 183/183 levels, 6,781 actions. **Estimated $158.32** API-price equivalent for a partial recorded research subtotal; actual complete cost is unknown. [Scorecard](https://arcprize.org/scorecards/60c10b53-9b8d-4af9-aae7-85f81543198a). The final runtime was [`2f258ff3`](https://github.com/uukuguy/asterion/tree/2f258ff3e74478805f63e08daa437acf9ca53a21); routes came from successive software revisions and retain their original identities and certificates.

By [Jiangwen Su](https://github.com/uukuguy) ([Hugging Face](https://huggingface.co/uukuguy)). [Software citation](submission.yaml).

## How the scorecard was produced

The public-game campaign was **warm-start iterative research**, with same-game experience accumulation, failed attempts, retries, verified prefix reuse, operator scheduling, selected cognition resets, and generic application/infrastructure repairs between attempts. It was not one empty-history, fixed-version, unattended run. The LLM generated game hypotheses, WorldMaps, programs, and candidate routes.

Save-time SDK replay checked progress and source/game identities and certified the selected routes. Official submission then executed those actions in new online Competition games **without model inference**. The scorecard normally closed, and its receipt was checked against every selected route. The 6,781 actions cover selected online routes, not earlier exploration; a Competition RESET itself counts as an action and does not discard preceding actions. [Per-game and per-level counts, runtime provenance, and usage scope](https://github.com/uukuguy/asterion/blob/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/docs/results/arc-agi-3/p7-public-2026-10-07.json).

This result concerns the 25 public games. It does not demonstrate fresh-model unseen-game performance or a private-set result. A source checkout includes the producing system but not the operator's private historical attempt records or certified roster. The read-only console shows local saved progress and replay; synchronization may lag research.

## Run the producing system

Use the [pinned reproduction guide](https://github.com/uukuguy/asterion/blob/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/docs/guides/prime-p7-community-reproduction.md) with the published `P7-2026-10-07` tag (source/documentation commit `bb005c5b`). Framework inspection needs Python 3.10+ and `uv`, without model credentials:

```bash
git clone https://github.com/uukuguy/asterion.git
cd asterion
git checkout P7-2026-10-07
uv sync --frozen
uv run asterion list
uv run asterion describe --provider dci-agent-lite
```

Live research needs separately prepared Pi/authenticated backend access, external ARC assets and SDK wheels (`arc_agi` 0.9.9 / `arcengine` 0.9.3), and private operator credentials. Current Make launchers target macOS/OrbStack with a systemd/cgroups Linux guest, guest Python 3.11+, and Node 22/npm with the resolver's offline package cache. Set `ASTERION_PRIME_PROVIDER=openai-codex` and `ASTERION_PRIME_MODEL=gpt-6.1-sol` explicitly; prepare `ARC_API_KEY` privately. The guide specifies resource-root/Pi-profile/guest overrides and bootstrap gaps; `make setup` alone does not finish P7 setup.

After those prerequisites, synchronize the public catalog and run one bounded OFFLINE attempt:

```bash
make asterion-prime-p7-sync-games
make asterion-prime-p7-games
make asterion-prime-p7-level-witness GAME=ls20 LEVEL=1
make p7-controller
```

Catalog sync uses GETs without a scorecard or model. The witness calls the model and applies a fixed 900-second guest allowance, an action ceiling, and cleanup checks. `LEVEL=N` completes levels 1 through N in order. Check the attempt summary for actual progress and failure; timeout/cap exhaustion is not a pass. The local console opens at `http://127.0.0.1:57515/`. New operators build their own experience and certified routes; this example does not recreate the historical 100-score campaign.

Once your own routes have valid certificates, explicitly choose online replay:

```bash
make asterion-prime-p7-official-preflight
make asterion-prime-p7-official-submit GAME=ls20
# Alternatively, for a separately chosen full-catalog submission:
make asterion-prime-p7-official-submit GAME=all
```

Preflight opens no card and calls no model. Submission creates a new Competition card, executes saved actions online without a model, and stops on uncertainty. Missing/stale certification is rejected before card creation; `GAME=all` needs a complete certified roster with the exact model identity. Only a checked `closed-confirmed` receipt establishes the final score.

## Usage and cost

**Actual complete monetary cost is unknown.** These recorded scopes overlap; do not add them:

| Recorded scope | Runs | Usage records | Input tokens, including cache | Output tokens |
|---|---:|---:|---:|---:|
| Sources selected for the final 25 routes | 25 | 618 | 65,878,471 | 301,489 |
| Scoped persisted P7 research cohort | 228 | 6,885 | 723,793,948 | 3,382,772 |

The 228-run subtotal uses a shared run-label prefix, not a uniform UTC+8 calendar day or full campaign ledger. All 228 hash chains validate: 220 sealed, 8 unsealed; 4 runs lack summaries and 1 has zero recorded usage. Interrupted requests may lack usage, and missing provider request IDs prevent proving cross-run deduplication.

The submission reports **estimated `cost: 158.32` USD** for the 228-run recorded subtotal at [public Standard API rates](https://developers.openai.com/api/docs/models/gpt-6.1-sol) checked on 2026-10-07, **assuming 97% cached reads and 3% cache writes**. If the remaining 3% instead uses the uncached-input rate, the alternative estimate is **$147.46**; Fast at 2× gives **$294.93–$316.64**. Cache categories/service mode were not retained, so 97% is an assumption, not a measured cache-hit rate. These are API-price equivalents, not actual payment or proven cost bounds. Earlier P7 research, supervisor/development work, missing usage, regional premiums, tool fees, and account discounts are excluded. Official replay's zero model calls do not imply zero research cost. The reported field is this conditional estimate, not an actual bill or complete campaign cost; [detailed rates, assumptions and exact values](https://github.com/uukuguy/asterion/blob/bb005c5bfb8406e7fc3c6f97d59138e90ace691f/docs/results/arc-agi-3/README.md#scoped-api-price-estimate) are in Asterion's result record.
