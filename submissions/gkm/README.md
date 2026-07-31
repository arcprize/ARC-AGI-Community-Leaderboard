# GKM submission summary

## What GKM is

The Gödel–Kolmogorov Machine (GKM) is a general-purpose, compute-bounded
program-growth architecture for interactive ARC-AGI-3. A native coding-model
proposer interacts with a game through one fixed Arena interface and writes
executable solver state: reusable `legs.py` skills, per-level `players.py`
bindings, perception routines, searches, planners, probes, and finite programs.
Fixed host code treats that output as an untrusted candidate. It admits a new
boundary only after source execution from reset, independent first-passage path
replay from another reset, action-protocol and taint checks, and a complete
hash/manifest chain.

The same producer contract, blank scaffold, interface, complexity coordinate,
evidence schema, and promotion rule are used across all 25 public games. Each
game has its own learned program because specialized executable knowledge is
the output of the general producer—not a separate human-authored architecture.

At scoring time no model runs. The receipt-bound Competition replayer reads the
admitted `final_path` from each frozen checkpoint and sends those actions
through the official API.

## Community Leaderboard criteria

**General-purpose.** GKM is general-purpose at the producer level. It begins an
unseen game with raw 64×64 frames, the public action interface, progress,
terminal state, reset, and uniformly available local clone lookahead. It is not
given object names, mechanics, goals, game source, or an answer program. The
coding model must infer those from interaction and synthesize the executable
solver.

Generated source may contain a generic search, a learned detector, a
parameterized interaction routine, game-specific coordinates, or a literal
finite plan. These are different kinds of learned program cells with the same
provenance: they were written inside model-proposal lineages and retained only
after host verification. Their specificity is not evidence that a human
hand-coded them. GKM's claim concerns one producer that repeatedly acquires new
executable knowledge, not one frozen action policy that must remain unchanged
across unrelated games.

Local `clone()` is a fixed discovery capability exposed uniformly by the GKM
Arena. It is not available or used during official scoring. The Competition
endpoint is a separate zero-LLM replay of the already admitted program paths.

**Open system, not just output.** The public source revision contains both:

- the producer, proposer adapters, prompts, scaffold, campaign scheduler and
  supervisor, containment boundary, source-complexity accounting, replay gate,
  certifier, release gate, and scorecard replayer; and
- the frozen model-generated acquisition source plus a normalized schema-v2
  tree containing exact source/path audits, taint and action-protocol audits,
  manifests, hashes, checkpoints, and the content-addressed release receipt.

The release intentionally excludes failed attempts, superseded archives, and
WIP clutter. Historical evidence from more than one acquisition schema is
normalized without falsifying provenance: if an old exact source boundary is
unavailable or no longer completes within the certification bound, the
certifier executes a minimal capsule reconstructed from the already validated
first-passage path and labels it
`deterministic_exact_path_reconstruction`. The original model-generated runtime
source remains separately preserved; reconstructed capsules are not presented
as historical source-growth observations.

**Novel contribution.** GKM makes the Gödel-machine/PowerPlay/compression
connection executable:

- a coding model proposes a new program cell and its attachment to the
  incumbent solver;
- independent replay is the admission gate;
- the verified archive grows monotonically and re-certifies shallower
  first-passage obligations;
- retained source description and behavioral gain define the
  Kolmogorov/free-energy selection coordinate; and
- exact adjacent source boundaries permit strict reuse witnesses, where a new
  player calls an unchanged prior leg and fresh replay verifies the
  composition.

The proposal language deliberately includes finite programs. Fair dovetailed
search therefore gives a compute-indexed completeness fallback for
deterministic, resettable games with finite winning traces; reusable legs,
model priors, curiosity, and description pressure make that search practical
by reusing structure instead of restarting from an unstructured enumeration.

## Authorship and authority

| Participant | Contribution | Authority |
|---|---|---|
| Fixed research harness | Arena, blank scaffold, proposer adapter, scheduler, complexity measure, containment, evidence schema, replay and release gates | Defines the experiment; does not supply learned per-game answer code |
| Native coding-model proposer | Writes game-playing legs, players, perception, probes, searches, planners, bindings, and finite programs | Candidate generation only |
| Campaign meta-supervisor | Allocates effort, selects clean continuation/restart, diagnoses infrastructure, and may request quarantined investigation | Scheduling and untrusted input only |
| Independent side expert | Investigates one difficult observation-derived obligation in isolation | No direct lineage or promotion authority |
| Trusted host verifier | Scans, executes, independently replays, seals exact boundaries, and atomically promotes | Sole promotion authority |
| Human operator | Defines the scientific question and resource envelope, monitors infrastructure, and chooses what to publish | Experimental governance, not silent solver-code authorship |
| Competition replayer | Sends frozen admitted actions to the official API | Scoring only; zero LLM inference |

The submission authors are **Alexander Kolpakov** and **OpenAI GPT-5.6**. The
v2 corpus also preserves legacy proposer lineages where applicable; each
retained boundary records its own provenance.

## Definitive v2 release

- Public release revision:
  [`9235ed26627140460efa1f6ca5e4041470cddc14`](https://github.com/sashakolpakov/gkm/commit/9235ed26627140460efa1f6ca5e4041470cddc14)
- Content-addressed release receipt:
  [`140e37ca7014d5aa6a48a3808fd94e90209c56499dbcd7df9f0fe733a29a7681`](https://github.com/sashakolpakov/gkm/blob/9235ed26627140460efa1f6ca5e4041470cddc14/arc/crack_lab/releases/arc_agi3_gkm_v2_181/receipts/140e37ca7014d5aa6a48a3808fd94e90209c56499dbcd7df9f0fe733a29a7681.json)
- Full ONLINE shakedown:
  [181/183 on all 25 games](https://arcprize.org/scorecards/e293eeae-c0de-4263-a916-0a40ad282cbc)
- Definitive Competition scorecard:
  [98.11664037825032%](https://arcprize.org/scorecards/cf75e14b-2c25-41cb-bc70-53bd57411edb)
- Official Competition score: **98.11664037825032%**
- Raw verified coverage: **181/183 = 98.907103825137%**
- Stored game actions: **7,001**
- Official Competition API actions: **7,069**
- Games replayed: **25/25**
- Proposer tokens used during scoring: **0**

| Game | Verified depth | Stored path actions |
|---|---:|---:|
| `ar25` | 8/8 | 269 |
| `bp35` | 9/9 | 393 |
| `cd82` | 6/6 | 91 |
| `cn04` | 6/6 | 210 |
| `dc22` | 6/6 | 540 |
| `ft09` | 6/6 | 80 |
| `g50t` | 7/7 | 361 |
| `ka59` | 7/7 | 342 |
| `lf52` | 8/10 | 544 |
| `lp85` | 8/8 | 93 |
| `ls20` | 7/7 | 365 |
| `m0r0` | 6/6 | 230 |
| `r11l` | 6/6 | 115 |
| `re86` | 8/8 | 600 |
| `s5i5` | 8/8 | 329 |
| `sb26` | 8/8 | 124 |
| `sc25` | 6/6 | 144 |
| `sk48` | 8/8 | 506 |
| `sp80` | 6/6 | 151 |
| `su15` | 9/9 | 170 |
| `tn36` | 7/7 | 131 |
| `tr87` | 6/6 | 208 |
| `tu93` | 9/9 | 195 |
| `vc33` | 7/7 | 213 |
| `wa30` | 9/9 | 597 |
| **Total** | **181/183** | **7,001** |

The definitive scorecard was generated only after the same receipt-bound
25-game payload passed local schema-v2 validation and a complete ONLINE
shakedown. The ARC-AGI-3 YAML intentionally contains the scorecard URL rather
than a self-reported numeric score, as required by this leaderboard.

The 7,001 stored actions are the immutable game paths. The official Competition
count also records one initial reset for each game and 43 actions from a
transient VC33 connection-reset attempt; level-boundary recovery replayed that
segment on the same scorecard and preserved the exact 7/7 result.

## Public evidence

- [Frozen v2 release and reproduction guide](https://github.com/sashakolpakov/gkm/tree/9235ed26627140460efa1f6ca5e4041470cddc14/arc/crack_lab/releases/arc_agi3_gkm_v2_181)
- [Producer and promotion loop](https://github.com/sashakolpakov/gkm/blob/9235ed26627140460efa1f6ca5e4041470cddc14/arc/crack_lab/gkm_legs.py)
- [Arena and independent replay](https://github.com/sashakolpakov/gkm/blob/9235ed26627140460efa1f6ca5e4041470cddc14/arc/crack_lab/gkm_arena.py)
- [Boundary certifier](https://github.com/sashakolpakov/gkm/blob/9235ed26627140460efa1f6ca5e4041470cddc14/arc/crack_lab/arc_agi3_boundary_certifier.py)
- [Release gate](https://github.com/sashakolpakov/gkm/blob/9235ed26627140460efa1f6ca5e4041470cddc14/arc/crack_lab/arc_agi3_release_gate.py)
- [Competition replayer](https://github.com/sashakolpakov/gkm/blob/9235ed26627140460efa1f6ca5e4041470cddc14/arc/crack_lab/replay_scorecard.py)
- [Normalized 181-level artifact tree](https://github.com/sashakolpakov/gkm/tree/9235ed26627140460efa1f6ca5e4041470cddc14/arc/crack_lab/releases/arc_agi3_gkm_v2_181/artifacts)
- [Frozen model-generated acquisition source](https://github.com/sashakolpakov/gkm/tree/9235ed26627140460efa1f6ca5e4041470cddc14/arc/crack_lab/releases/arc_agi3_gkm_v2_181/acquisition_source)
- [Detailed submission README](https://github.com/sashakolpakov/ARC-AGI-Community-Leaderboard/blob/gkm-submission/submissions/gkm/README.md)

Proposal sampling is stochastic, so a clean reacquisition need not reproduce
byte-identical source. The published endpoint claim is exact: the frozen source
bytes, action paths, audit records, manifests, receipt, ONLINE run, and
Competition scorecard are all linked to one public revision and can be checked
without trusting a model's prose.
