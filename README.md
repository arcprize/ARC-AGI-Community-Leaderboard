# ARC Prize Community Leaderboard

A community-driven showcase of ARC-AGI methods, harnesses, and approaches for [ARC-AGI](https://arcprize.org). Open to anyone - submit via Pull Request.

This is a curated showcase of methods, not a ranking. Although self-reported scores are collected with each submission, there's no reliable way to validate them - so we don't display them on the website. Only [ARC Prize Verified](https://arcprize.org/leaderboard) scores are shown, with a number and badge. We want to highlight the system and the idea, not the score.

## What Belongs Here

This is a **showcase of novel, general-purpose, open methods** for ARC-AGI (v1, v2, or v3) - not a competition and not a ranking. We highlight the *system and the idea*, not the score. The goal is to promote interesting, net-new work.

A submission belongs here if it meets all three bars:

1. **General-purpose.** The method should plausibly work on tasks or games it has never seen. Per-task hardcoding, human-derived answer keys, or lookup tables of solutions don't belong here - even with a high score.
2. **The _system_ is open - not just the output.** The code that *produces* your results must be public and reproducible. Publishing only generated solutions (e.g. a file of per-task Python) without the system that created it is not enough.
3. **Novel contribution.** A new harness, search strategy, training method, or approach - one new idea. Novel wrappers around frontier models are welcome.

### About scores

Although we collect scores, self-reported scores are **untrustworthy by design**. We don't run Community Leaderboard code, nor verify scores against the ARC-AGI Semi-Private sets. So:

- We **collect** your score and cost in `submission.yaml`. For ARC-AGI-3 we collect a required `scorecard_url` and derive the score from it instead of taking a self-reported number.
- We **do not display** self-reported or derived scores, or costs, on the website.
- The only numbers shown are **ARC Prize Verified** scores (with the verified badge). For verified scores, see the [official leaderboard](https://arcprize.org/leaderboard).

But an untrustworthy score doesn't make a submission any less interesting. We rely on community verification to surface what's genuinely cool about these methods - we judge the idea and the method, not the number.

## How to Submit

Fork the repo, copy `submissions/.example/` to `submissions/<your-id>/`, fill in `submission.yaml`, and open a Pull Request. A maintainer reviews and merges submissions on a weekly basis.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full how-to - required fields, the submission schema, and the review process.

## Links

- [ARC Prize](https://arcprize.org)
- [ARC-AGI Benchmark](https://arcprize.org/arc-agi)
- [Community Leaderboard](https://arcprize.org/leaderboard/community)
- [Discord](https://discord.com/invite/9b77dPAmcA)
