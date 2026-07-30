# The Gödel–Kolmogorov Machine (GKM)

GKM is a compute-bounded self-improving architecture for interactive
ARC-AGI-3. It joins four ideas in one executable system:

- a **Gödel-machine gate**: proposed self-revisions become real only after an
  independent certificate;
- a **PowerPlay archive**: each verified solver is retained, extended with the
  next task, and replayed to prevent forgetting;
- **Kolmogorov/free-energy selection**: progress is evaluated jointly by
  behavioral gain and retained program description;
- **inverse-colimit program growth**: a coding model proposes new executable
  components and the interfaces by which they attach to the incumbent solver.

Operationally, GKM is a meta-loop in which a coding LLM writes and extends a
per-game `legs.py` skill library plus thin per-level `players.py` bindings. A
candidate is promoted only when a fresh local replay confirms that it reaches a
new level. Each game has its own generated `<game>_legs/` program history; the
same producer, verifier, and retention protocol drives all of them.

The coding model does more than choose the next action. It constructs executable
objects—perception routines, searches, planners, interaction skills, and finite
plans—and binds them into the current program. A fixed host then compiles,
executes, independently replays, measures, and either rejects or promotes the
candidate. The promoted object is therefore a verified construction history,
not merely a final answer:

\[
X_{k-1}\hookrightarrow
P_k=X_{k-1}\sqcup_{A_k}B_k
\simeq_{\mathrm{replay}}X_k .
\]

Here \(X_{k-1}\) is the incumbent solver, \(B_k\) is a model-proposed executable
cell, \(A_k\) is its interface, the attaching map binds that interface to
incumbent code, \(P_k\) is the linked candidate, and \(X_k\) is the retained
replay-equivalent artifact. In the repository these data are concrete Python
definitions, signatures, calls, bindings, source snapshots, paths, and replay
certificates.

The authorship boundary is important: the game-playing source in generated
`agent_solutions/<game>_legs/legs.py` and `players.py` is written inside coding-
model proposer turns. A generic search, a learned object detector, a
parameterized interaction routine, a coordinate binding, and a literal finite
plan are all model-produced solver cells. The model writes ordinary Python, but
the human operator did not populate those per-game answer programs. Fixed
scaffold and generic
infrastructure are kept separately in the version-controlled harness. The
repository's later solution corpus contains many model-generated legs across
many games; no one particular routine is the architecture.

## Why this is a general method

The general object is the **producer and verifier**, not the task-specific
program that producer learns.

Every game begins behind the same interface:

```text
reset() -> frame
step(action) -> frame
frame() -> raw 64×64 grid
levels_completed
actions
terminal()
clone()
```

No interface field names the objects, mechanics, or goal. The same proposer
loop, workspace discipline, composition rule, complexity coordinate, taint
boundary, replay gate, and promotion rule can start from an empty solver on an
unseen game. Applying that method produces specialized executable knowledge,
just as a program synthesizer produces a task-specific program. Those learned
artifacts may range from general searches and parameterized skills to compact
finite plans; they are produced from interaction, not supplied as human answer
keys.

Literal finite action programs are deliberately inside the proposal language.
They give GKM a completeness fallback: for a deterministic resettable game with
a finite action alphabet and finite winning trace, fair dovetailed enumeration
finds a winning program in finite computation. With a stochastic proposer whose
per-stage success probability remains bounded below, the probability of an
unfinished finite game tends to zero as trials grow. Reusable legs, inherited
program structure, model priors, curiosity, and free-energy ordering are what
reshape that otherwise astronomical waiting time.

The linked scorecard demonstrates one finite-budget prefix of this monotone
search process. It is not the definition of the architecture or its ceiling.

## The self-improvement cycle

At frontier \(k\), GKM performs the following cycle:

1. Seed an isolated workspace from the highest replay-verified artifact.
2. Ask the native coding-model proposer to solve the next obligation by
   composing incumbent legs first, then inventing missing executable objects and
   bindings where necessary.
3. Link the shared `legs.py`, thin per-level `players.py`, and `solve.py`
   dispatcher into one candidate program.
4. Treat all proposer output as untrusted: scan the transcript and workspace for
   hidden-source/private-runtime access and invalid action use.
5. Execute the candidate from reset, record its full action path, and replay that
   path independently from a second reset.
6. If and only if replay reaches a new depth, retain the exact winning source,
   checkpoint, path, source delta, and provenance; otherwise preserve it only as
   unpromoted work.
7. Optionally ask the model to factor repeated glue into a higher-order leg, then
   execute and replay again before retaining the refactor.

A successful depth-\(k\) replay also re-certifies every shallower obligation by
first-passage truncation. This is GKM's executable no-forgetting condition: a
new solver may use a better route, but it must still reproduce all prior depths.

The implementation is public:

- [producer and promotion loop](https://github.com/sashakolpakov/gkm/blob/91606141db241964d3833c340f9354c6dbdc53db/arc/crack_lab/gkm_legs.py)
- [Arena adapter and fresh replay](https://github.com/sashakolpakov/gkm/blob/91606141db241964d3833c340f9354c6dbdc53db/arc/crack_lab/gkm_arena.py)
- [scorecard replayer](https://github.com/sashakolpakov/gkm/blob/91606141db241964d3833c340f9354c6dbdc53db/arc/crack_lab/replay_scorecard.py)
- [taint audit](https://github.com/sashakolpakov/gkm/blob/91606141db241964d3833c340f9354c6dbdc53db/arc/audit_submission_taint.py)
- [generated solver archive at the scored revision](https://github.com/sashakolpakov/gkm/tree/91606141db241964d3833c340f9354c6dbdc53db/arc/crack_lab/agent_solutions)
- [reproduction guide](https://github.com/sashakolpakov/gkm/blob/249cac85a4b5a65870ff201463290b0e2381d8e3/REPRODUCE_ARC.md)
- [manuscript source](https://github.com/sashakolpakov/gkm/blob/249cac85a4b5a65870ff201463290b0e2381d8e3/arc/manuscript/arc_agi3.tex)

Commit
[`91606141`](https://github.com/sashakolpakov/gkm/commit/91606141db241964d3833c340f9354c6dbdc53db)
is the frozen GKM source revision associated with the linked July scorecard.
Commit
[`249cac85`](https://github.com/sashakolpakov/gkm/commit/249cac85a4b5a65870ff201463290b0e2381d8e3)
is used only for later method and reproduction documentation. Keeping the two
revisions explicit prevents later artifacts from being silently substituted
into the historical score.

## What each participant contributes

“Hand-coded or automatic?” is not a useful binary for a system with several
separate authorities. The provenance boundary is:

| Participant | Contribution to GKM | Evidence/authority |
|---|---|---|
| Research harness | Supplies the game-independent Arena interface, workspace schema, generic scaffold, proposer adapter, description metric, replay gate, artifact store, and scorer | Version-controlled before each native acquisition turn; it defines the experiment but does not contain a game's learned solution |
| Native coding-model proposer | Interacts through Arena and writes the game-playing `legs.py`, `players.py`, probes, searches, planners, bindings, and finite plans | Its tool writes and post-turn workspace identify the source it generated; it cannot certify or promote itself |
| Session meta-proposer/supervisor | Allocates proposal effort, selects clean continuation versus restart, diagnoses harness failures, and may formulate an observation-derived tactical handoff on difficult frontiers | A separate campaign-level role; its handoff remains an untrusted input to a native turn and has no replay or promotion authority |
| Independent side expert | Investigates a distinct same-frontier obligation in a private copy and may return a hypothesis or candidate stream | Quarantined until reproduced in an admitted native lineage and passed by the ordinary host gate |
| Trusted host verifier | Reopens source and transcript evidence, enforces taint/action policy, runs fresh execution and replay, captures the winning boundary, and promotes | The only component with admission authority; model assertions never substitute for replay |
| Human research operator | Chooses the scientific problem and resource constraints, authorizes runs, monitors failures, and decides what to publish | Governs the experiment; does not thereby become author of code written inside a recorded native proposer turn |
| Competition replayer | Reads a retained checkpoint path and submits its actions to the ARC Prize API | Deterministic, zero-LLM scoring step |

The linked July score used the native-proposer/replay-gate architecture. The
campaign-level meta-proposer and independent side-expert roles are later
extensions of the same scientific program and are listed so that scheduling,
solver authorship, verification, and human governance are not conflated.

## The Kolmogorov/free-energy coordinate

For a retained solver \(s\), GKM records a computable description coordinate
\(D_\kappa(s)\): nonblank, noncomment lines in the shared leg and player files,
plus AST container-literal elements so that a long path on one source line is
not assigned unit cost. With risk \(R(s)\) equal to the number of levels not yet
replayed, candidate structure is evaluated on

\[
\Phi(\lambda)=\inf_s\bigl(R(s)+\lambda D_\kappa(s)\bigr).
\]

The historical construction ledger separately charges positive retained growth
at each promotion. This makes the predicted sawtooth observable: a new mechanic
can raise conditional description, while a later task that binds an unchanged
leg can require much less new source.

A numerical drop alone is not labeled reuse. GKM's strict witness requires:

1. exact winning source at adjacent replay-valid boundaries;
2. conditional novelty computed under the same representation;
3. a winning player that directly calls an unchanged earlier leg; and
4. fresh replay of the composite.

The manuscript's exact checkpoint audit identifies such coupled witnesses. This
is the empirical content of the inverse-colimit claim: the old executable cell
survives, and the new promotion mainly pays for its attaching map and residual
glue.

## Frozen Competition scorecard

The [public Competition-Mode scorecard](https://arcprize.org/scorecards/9e166671-0953-42f3-89de-a0fd57d7b147)
records the following frozen endpoints:

| Game | Replayed depth | API actions |
|---|---:|---:|
| `wa30` | 9/9 | 597 |
| `ls20` | 7/7 | 394 |
| `ft09` | 4/6 | 47 |
| `g50t` | 4/7 | 146 |
| `r11l` | 4/6 | 46 |
| `sp80` | 4/6 | 80 |
| `tr87` | 4/6 | 127 |
| `tu93` | 1/9 | 19 |
| **Total** | **37/183 across the complete public suite** | **1,456** |

The card's official all-game score is **17.1365079365%**; the separate raw
level fraction is **37/183 = 20.2186%**. The API action total includes one reset
for each of the eight attempted games, hence eight more actions than the stored
paths. Competition replay invokes no coding model: it deterministically sends
the already admitted paths and checks remote depth.

## Reproduction

The repository exposes three distinct reproducibility layers:

1. **Artifact integrity:** verify retained source/checkpoint histories, hashes,
   action encodings, and promotion invariants.
2. **Endpoint behavior:** replay admitted programs locally and then through the
   remote ARC interface, with no proposer inference.
3. **Method replication:** run the public producer on clean game workspaces to
   generate new stochastic proposal histories, each subject to the same
   deterministic admission rule.

The first two reproduce the reported artifacts exactly. The third reproduces
the scientific process: stochastic model sampling need not emit byte-identical
programs for the resulting verified construction history to be independently
testable.

The key commands and evidence locations are documented in
[`REPRODUCE_ARC.md`](https://github.com/sashakolpakov/gkm/blob/249cac85a4b5a65870ff201463290b0e2381d8e3/REPRODUCE_ARC.md).
