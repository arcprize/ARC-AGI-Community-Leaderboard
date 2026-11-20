# CAEL: non-neural program search with a self-checking swarm

No neural network is involved. `cael_unified/arc_solver.py` runs 53 solver families; each candidate rule must reproduce
every demonstration pair before it may predict. Candidates are ranked by description length plus a small per-family
prior, the task is solved under all 8 grid symmetries and the answers vote, and when answers compete each leading rule
is learned again with one demonstration held out and must predict it. Two attempts per test input.

**Reproduce** (CPU, about 3–5 minutes for 400 tasks with 14–16 workers):

```bash
git clone https://github.com/Vovala14/CAEL && cd CAEL && git checkout v0.4.4
python -m pip install -r requirements-unified.txt
git clone https://github.com/fchollet/ARC-AGI
python evaluate_arc.py --data ARC-AGI/data/evaluation --out results/my_arc_eval
```

Per-task results: [results/arc_agi_1_evaluation_0.4.4.jsonl](https://github.com/Vovala14/CAEL/blob/v0.4.4/results/arc_agi_1_evaluation_0.4.4.jsonl)
(62 of 400 solved, pass@2, 10 s per task). ARC-AGI-2 public evaluation: 0 of 120.

**Honest note:** the solver families were developed on the ARC-AGI-1 training set only (152 of 400 solved there), but
the public evaluation set was scored at several development milestones, so 15.5% is a repeated look rather than a
single blind run. Results on unseen sets are very welcome.
