# Affine.Earth (`affine-uum8d-s4`) — ARC Prize Community Leaderboard Submission

## Open Solver Implementation & Reproducible Run Configuration

Unlike thin API client wrappers, the complete offline ARC-AGI-2 solver that turns an unseen ARC task JSON (`train` demonstration pairs + `test` input grids) into validated `attempt_1` / `attempt_2` grid predictions is published in [`gaiaftcl-sudo/affine.earth.public`](https://github.com/gaiaftcl-sudo/affine.earth.public):

- **Primary Hybrid Solver Kernel (`LOCAL_HYBRID_SOLVER`):** [`llm_llvm_bench/arc/local_hybrid_solver.py`](https://github.com/gaiaftcl-sudo/affine.earth.public/blob/main/llm_llvm_bench/arc/local_hybrid_solver.py) — combines 8-marker grid readout, replay-gated discrete DSL candidate synthesis (dihedral $D_4$, connected-component & subgrid invariants), and demonstration-gated `icecuber` search (`ARC_ICECUBER_DEPTH=2` default, `1..4` configurable). Candidate transforms must exact-match 100% of `train` demonstration pairs before emitting test grid predictions; `[[0]]` and `[[]]` placeholders are rejected.
- **Standalone Offline Evaluation Driver:** [`scripts/arc_local_mastery.py`](https://github.com/gaiaftcl-sudo/affine.earth.public/blob/main/scripts/arc_local_mastery.py) & [`bin/run-arc-local-mastery.sh`](https://github.com/gaiaftcl-sudo/affine.earth.public/blob/main/bin/run-arc-local-mastery.sh)
- **Air-Gapped Kaggle Runner:** [`kaggle/arc-prize-2026-agi-2/arc_agi_2_kaggle.py`](https://github.com/gaiaftcl-sudo/affine.earth.public/blob/main/kaggle/arc-prize-2026-agi-2/arc_agi_2_kaggle.py)

### Local Reproduction Command

```bash
git clone https://github.com/gaiaftcl-sudo/affine.earth.public.git
cd affine.earth.public
python3.12 -m pip install -e ".[dev]"
ARC_ICECUBER_DEPTH=2 ARC_LOCAL_PYTHON=python3.12 ARC_LOCAL_PARQUET_PYTHON=python3 \
  ./bin/run-arc-local-mastery.sh --report-dir reports/arc_local_eval
```

## Reconciled Public Evaluation Outputs (`ARC-AGI-2` Public Set)

- **Scope Qualification:** Self-reported community evaluation on the labeled **ARC-AGI-2 public evaluation set** (`arc-agi_evaluation_challenges.json`: **120 task IDs / 172 test grids**), not an ARC Prize Semi-Private Kaggle verification score. The earlier `arc-agi-1` entry and synthetic 2-row `arc-agi-3-lattice` sample have been removed/replaced so every reported entry maps 1-to-1 to the published 120-task / 172-grid output artifact:
  1. **Canonical Kaggle-Schema JSON (`120` task keys, `172` test grids):** [`reports/arc_local_20260721T172649Z/agi2/submission.json`](https://github.com/gaiaftcl-sudo/affine.earth.public/blob/main/reports/arc_local_20260721T172649Z/agi2/submission.json) (schema-checked via `scripts/validate_arc_prize_submission.py`).
  2. **Per-Task JSONL Mirror (`120` rows):** [`uum8dSolarResearch/submissions/arc_agi_3_community/predictions.jsonl`](https://github.com/gaiaftcl-sudo/uum8dSolarResearch/blob/main/submissions/arc_agi_3_community/predictions.jsonl) and Hugging Face [`rpg67/Affine.Earth-Benchmarks` (`arc_agi_2` split)](https://huggingface.co/datasets/rpg67/Affine.Earth-Benchmarks).
