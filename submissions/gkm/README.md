# GKM: replay-gated program growth

GKM grows executable ARC-AGI-3 solvers as a library of reusable *legs*. A coding
proposer may add perception, search, planning, or literal replay structure, but a
candidate is promoted only after a fresh replay verifies that it reaches the claimed
level. The public scorecard replays the final promoted paths for `wa30` (9/9) and
`ls20` (7/7) through the official API; discovery used a stronger local research
interface with `clone()` lookahead, so the work does not claim official-interface
sample efficiency.

Using the unchanged harness and promotion protocol, a bounded follow-on campaign also
reached replay-validated L4 endpoints on `ft09`, `g50t`, `r11l`, `sp80`, and `tr87`.
These partial endpoints are not additions to the linked scorecard, but they leave
additional proposer compute as the remaining operational requirement for broader game
coverage rather than another game-specific solver architecture.

## Complexity drop under reuse

For each promotion, the historical `marginal_C` field records positive net retained
description-size growth in `legs.py` and `players.py`, plus charged literal containers.
It is an auditable source-growth statistic, not an estimator of Kolmogorov complexity:
additions and deletions within one file are netted, so a same-size replacement may score
zero. Consequently, low values are evidence of reuse only when source provenance shows
that the relevant legs stayed unchanged and the resulting composition passes replay.

The complete `ls20` ledger is:

| Level | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| `marginal_C` | 43 | **2** | 45 | **3** | 72 | 130 | 67 |

The `43 -> 2` and `45 -> 3` collapses occur when thin level players compose unchanged
search legs. New frame noise, recovered plan artifacts, and the lock/display mechanic
produce larger increments. The resulting sawtooth is the relevant transfer signature:
complexity falls under demonstrated reuse and rises when the retained solver must grow.
The scalar alone does not identify novelty; that attribution comes from the paired
source snapshots and fresh replay.

## Schmidhuber lineage

The design operationalizes three related ideas from Juergen Schmidhuber's work:

- **[Goedel machines](https://doi.org/10.1007/978-3-540-68677-4_7):** a program may revise executable problem-solving code, but GKM
  replaces a formal global proof with the narrower empirical obligation of a successful
  fresh replay.
- **[PowerPlay](https://doi.org/10.3389/fpsyg.2013.00313):** the solver is extended incrementally while previously promoted skills
  remain available as a shared library.
- **[Compression progress and artificial curiosity](https://doi.org/10.1109/TAMD.2010.2056368):** a drop in retained source growth
  when a new level reuses existing legs is treated as a learning-progress signal. GKM
  audits this signal against code and replay rather than equating it with semantic
  novelty or true Kolmogorov complexity.

The [paper and documentation](https://sashakolpakov.github.io/gkm/) give the formal
motivation and limitations. The public repository contains the
[promoted artifacts, complete ledgers, clean-source hashes, and preserved WIP](https://github.com/sashakolpakov/gkm/tree/master/arc/crack_lab/agent_solutions)
needed to audit the result.
