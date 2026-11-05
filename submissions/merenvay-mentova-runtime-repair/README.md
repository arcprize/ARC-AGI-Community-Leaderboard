# MERENVAY Training-Derived Symbolic Baseline

This entry submits a standalone Python baseline that scored **0.0%** on the complete ARC-AGI-2 public evaluation set: **0/167 exact test outputs**, with **0/120 tasks** having all test outputs correct, using at most two attempts per test input. This is the actual negative result for its limited grammar.

It replaces the earlier unmerged Mentova runtime-repair submission in PR #62, following [Matt's follow-up](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/pull/62#issuecomment-6664282449). The submitted method imports neither Mentova nor its task-specific rule library. No earlier method's result is attributed to this baseline. The original submission directory is retained for update continuity.

## Method and contribution

For each task, the solver enumerates a fixed grammar of D4 rotations/reflections, nonzero-foreground cropping, 2x/3x nearest-neighbor scaling, 2x2 tiling, shape/D4 compositions in either order, and compositions of two different shape operators. It optionally infers a color mapping from all visible training examples; unseen colors remain unchanged. Candidates are accepted only if they match every training input/output pair within the fixed search budget. Task IDs serve only as output record keys.

Accepted programs rank by operation cost and name. A candidate must run on every test input of the task; candidates that cannot are excluded for the whole task. The first two distinct complete prediction sequences are selected, and those same programs supply the two attempts for every test grid. If only one sequence remains it is duplicated; if none remains the solver emits identity outputs for the whole task as an explicitly unverified fallback. Prediction accepts training examples and unlabeled test inputs only; test-output fields are rejected.

The concrete contribution is the independently implemented, inspectable baseline with task-level strategy freezing, complete-sequence deduplication, synthetic regression controls, and a separate scorer for frozen predictions. Its elementary operators and program-enumeration approach are established techniques; no new class of program synthesis or broad ARC-solving breakthrough is claimed. The system runs locally with Python, without learned weights, a hosted model, or an external solver.

## Self-reported ARC-AGI-2 public result

| Item | Frozen evaluation record |
| --- | --- |
| Dataset | [Official ARC-AGI-2](https://github.com/arcprize/ARC-AGI-2/tree/f3283f727488ad98fe575ea6a5ac981e4a188e49), commit `f3283f727488ad98fe575ea6a5ac981e4a188e49` |
| Scope | All 120 tasks in `data/evaluation/`, matched to `data/evaluation.txt`; all 167 test inputs |
| Attempt limit | At most two grid attempts per test input; the same two selected programs across all test inputs of each task |
| Metric submitted in YAML | **0.0%**: `100 * mean(correct test outputs / test outputs for each task)`; either attempt may match |
| Output-weighted diagnostic | **0/167** exact test outputs (**0.0%**) |
| All-tests-correct diagnostic | **0/120** tasks |
| Process/schema failures | None; every task and test input produced valid predictions |
| Search defaults | At most 256 candidates and 512 validation demonstration checks per task; color-map fitting scans are outside that check counter |
| Published source/evidence | Commit `7a89d10f82cb5d6767a35c8db9017437cd0b3081` |
| Unchanged solver source | Based on `be73bc4917f2877abae0dfd36736b1a6e8117049`; SHA-256 `37084696d0040d26ce08fc3d18e0cea20f78436152abb4ba59b9a24add01e769` |
| Prediction freeze | SHA-256 `d3bb5745077d6c638b626ad1220e7eab31d25c89e771dc1256c6b0fbada2de83` |
| Score artifact | SHA-256 `aff5edcc9d287b4234b128a3763e47b59c2fb44750a7440bfd226ebd8f251072` |
| Reproduction record | [Pinned evaluation receipt](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/blob/7a89d10f82cb5d6767a35c8db9017437cd0b3081/research/arc62_training_derived/results/20261105_public_evaluation/README.md) |

Predictions and their manifest were frozen before a separate scorer process read expected test outputs. The inference subprocess received only the projected training pairs and unlabeled test inputs. This is process/data-flow separation; labeled public source data remained on the same host. No solver change or score-driven tuning followed this trial.

This is a self-reported public-set measurement, without ARC Prize verification. Public-set performance does not establish hidden-set generalization. Cost is omitted because no audited monetary cost was measured.

## Public code and reproduction

- [Method directory and instructions](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/tree/7a89d10f82cb5d6767a35c8db9017437cd0b3081/research/arc62_training_derived)
- [Standalone solver](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/blob/7a89d10f82cb5d6767a35c8db9017437cd0b3081/research/arc62_training_derived/generic_solver.py)
- [Synthetic solver and evaluator controls](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/tree/7a89d10f82cb5d6767a35c8db9017437cd0b3081/research/arc62_training_derived/tests)
- [Frozen evaluation procedure](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/blob/7a89d10f82cb5d6767a35c8db9017437cd0b3081/research/arc62_training_derived/evaluate_public.py)
- [Evaluation receipt](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/blob/7a89d10f82cb5d6767a35c8db9017437cd0b3081/research/arc62_training_derived/results/20261105_public_evaluation/README.md), [score](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/blob/7a89d10f82cb5d6767a35c8db9017437cd0b3081/research/arc62_training_derived/results/20261105_public_evaluation/score.json), [predictions](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/blob/7a89d10f82cb5d6767a35c8db9017437cd0b3081/research/arc62_training_derived/results/20261105_public_evaluation/predictions.json), and [frozen manifest](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/blob/7a89d10f82cb5d6767a35c8db9017437cd0b3081/research/arc62_training_derived/results/20261105_public_evaluation/frozen_manifest.json)

From a clean checkout of the published method commit, with an official dataset clone at the recorded revision:

```sh
python -B research/arc62_training_derived/evaluate_public.py run \
  --dataset /path/to/ARC-AGI-2 --output /path/to/a/new/result-directory
python -B -m unittest discover -s research/arc62_training_derived/tests -v
```

The runner refuses to overwrite an existing result directory. It projects challenge-only input, generates and freezes predictions, and launches a separate scorer. The receipt retains exact commands, process times, return codes, denominators, hashes and the aggregate calculation. All **25 software tests passed**: 18 synthetic solver controls and seven scorer/projection controls. These tests establish specific mechanics, not public benchmark accuracy.

## Limits

The grammar has no general object decomposition, counting, advanced relational rules, or recursive program invention. Matching all demonstrations can leave several hypotheses; the fixed ranking may select the wrong one, and identity fallback can be wrong. Search limits can exclude a fitting program. The zero public score demonstrates the limited coverage of this frozen version. The public evaluation is descriptive and does not show that development was free from all public-benchmark exposure.
