# Gödel–Kolmogorov Machine (GKM), version 3

GKM uses a coding-model proposer to acquire executable skills through interaction
with ARC-AGI-3. It retains a library of solver components and level bindings after
execution, independent replay, action-protocol, taint and provenance checks. This
verified-component approach is inspired by Jürgen Schmidhuber's Gödel-machine and
PowerPlay programme.

## New GPT-6.1 acquisition

Version 3 publishes a new campaign using **GPT-6.1-sol throughout**, beginning each
game with an empty solver lineage. It reaches **182/183 public levels across all
25 games**, completing 24 games. Only lf52 level 10 is unclaimed. The admitted paths
contain **6,685 actions**; this is separate from official API resets and action
accounting. The closed [Competition-Mode scorecard](https://arcprize.org/scorecards/fb027490-5351-4a77-85f2-41959e3e6b64)
reports **99.27272727%**; raw level coverage is 99.4536%.

The same documented frame/action/reward interface and clone scaffold apply across
games. Model-generated code supplies all game-specific mechanics, searches,
coordinates and solver bindings. The host supervisor orchestrates, replays, audits
and admits; it supplies no game-specific solution advice. Discovery uses local
clone lookahead. Scoring replays the frozen paths through the official API with
no model inference or clone calls.

Admission accepts the first candidate that meets the exact progress, replay,
action and provenance requirements. Complexity and free energy are recorded after
admission as diagnostics. They do not rank candidates or enforce a universal cost
threshold or a prescribed sawtooth curve.

## Open producer and reproducible evidence

- [Frozen release and acquired source](https://github.com/sashakolpakov/gkm/tree/58d6038bdf8d57475a714bcbe81485c805197d3b/arc/crack_lab/releases/arc_agi3_gkm_v3_182)
- [Acquisition-time source closure](https://github.com/sashakolpakov/gkm/tree/58d6038bdf8d57475a714bcbe81485c805197d3b/arc/crack_lab/releases/arc_agi3_gkm_v3_182/producer_source)
- [Campaign-control snapshot](https://github.com/sashakolpakov/gkm/tree/1492eeb7817950e2e943b05880907f5edcc6f445)
- [Publication verification context](https://github.com/sashakolpakov/gkm/tree/194b3a16af6ac0e1dcbd436aace15dc4783d99ea)
- [Reproduction instructions](https://github.com/sashakolpakov/gkm/tree/58d6038bdf8d57475a714bcbe81485c805197d3b/arc/crack_lab/releases/arc_agi3_gkm_v3_182/REPRODUCE.md)
- [Downloadable evidence archive](https://github.com/sashakolpakov/gkm/releases/tag/gkm-v3-gpt61-182)

All 182 boundaries passed fresh execution of the acquired solver source and an
independent path replay under the fixed 600-action full-game limit. No deterministic
action-only source reconstruction was needed. The release preserves all original
winning promotion chains, source and transcripts, plus separately normalized
schema-v2 evidence and a content-addressed partial-release receipt. The protocol
documents containment repairs, discarded descendants and strengthened re-audits;
those excluded histories are not claimed as accepted source-free solutions.

The later verification context extends the archived control manifest to cover the
GPT-6.1 scheduler, policy and integrity recognizer. It changes no discovery code or
learned solver. Publishing generated solutions alone would not reproduce the method;
the acquisition-time source closure, prompt, blank-start protocol and retry ladder
are public too.

The closed ONLINE and Competition public records pass the partial-release
validator. Original SDK collector FAIL receipts are retained alongside those
separate validations; the [scorecard note](https://github.com/sashakolpakov/gkm/blob/58d6038bdf8d57475a714bcbe81485c805197d3b/arc/crack_lab/releases/arc_agi3_gkm_v3_182/scorecards/README.md) explains the postflight payload differences.
The Competition action replayer itself is pinned to `a5b301d328d04d4b771bd36dd299b79939a93c36`;
the later publication adds evidence and accounting labels.

## Reporting cutoff and token accounting

This submission reports acquisition through retrospective retry n125 at the final
clean frontier: execution 454, closed on November 24, 2026. All retained promotions
predate that cutoff. An over-budget diagnostic path completes all ten lf52 levels
in 641 actions, 41 beyond the fixed limit; it is excluded from the claimed result.

Only usage through this cutoff is included below and in the version-3 YAML cost.
The counters include failed, discarded and infrastructure attempts within that
window. Terminal usage is available for 451 of 454 proposer turns; three
interrupted turns have unknown usage and remain unpriced.

| Recorded tokens through cutoff | Count |
| --- | ---: |
| Input, including cached input | 1,797,570,821 |
| Cached input (included above) | 1,758,867,584 |
| Uncached input | 38,703,237 |
| Output, including reasoning | 22,886,441 |
| Reasoning output (included above) | 16,049,437 |

At [standard GPT-6.1-sol API rates](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
($2 per million uncached input tokens, $0.10 per million cached input tokens and
$10 per million output tokens), the recorded-token API-equivalent cost through
the cutoff is **$482.16**. Cached input and reasoning output are subsets of their
respective totals and are not counted twice. This is a standard-rate valuation of
reported tokens, not a billing invoice. Host orchestration, local compute and
subsequent scorecard replay are outside proposer-token accounting.

Public solution replay measures neither the full discovery process nor held-out
generalization. Model-token accounting and game-action accounting are published
separately.

## Papers and historical versions

The selected manuscript, [Kolmogorov Structure Functions, Inverse-Colimits, and
Cofibrations: Solving ARC-AGI-3 with Compute-Bounded Self-Improving Agents](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7115218),
currently analyses the older GPT-5.6 dataset. The new replication is published
separately. The theoretical companion is [Pushout Attachments and Conditional
Complexity of Executable Models](https://arxiv.org/abs/2609.25024).

Versions 1 and 2 remain historical entries. Version 2 replaced the older wa30
lineage; the version-1 carry/relay-guided artifact remains excluded from the
observation-only discovery claim. Version 3 imports no solver or working notes
from either earlier release.
