# MERENVAY E-RNA — review supplement, 14 November 2026

This note accompanies PR #65 and its unchanged [pinned release](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/tree/32f309c2b4acf7cf6b4dd2a12c7b5edb0c0e73ca). It adds corrections and reproduction evidence; it does not replace the submitted method, alter its code, or turn the development result into a public-evaluation score.

## Result and interpretation

The recorded seed-0 comparison on 40 public ARC-AGI-2 **training** tasks is 1/40 for the symbolic baseline, 1/40 for the generator without residual proposals, and 2/40 with residual proposals. There is one feedback-only discordance, below the preregistered ten-discordance threshold. The comparison is uninformative for an improvement claim. This is not an ARC Prize Verified, hidden-set, competition or public-evaluation score.

## Corrections to read with the release

1. Shared operator implementations, static seeds and a sampler do not establish equal overall parameter support: residual derivation can emit parameters outside the sampler's support.
2. The no-feedback control is weak for the mirror illustration. Static shape proposals or systematic mirror enumeration could also find the program. The trace demonstrates a residual-conditioned next attempt, not a necessary or causal feedback advantage.
3. Candidate/check caps omit some derivation, precheck and other work. They are not total-compute accounting; the stored wall times are not speed evidence.
4. Five residual-derived programs matched the training demonstrations, but only one recorded task answer used a selected residual-derived program. The method is hand-designed, task-local and limited to two steps, with an unverified identity fallback when no accepted program is usable.
5. One packaged unit test slices a list with `[:0]` and is vacuous. Its passing status does not verify the intended property.
6. Prior familiarity with public training task types is not excluded. Local hashes establish consistency, not independently authenticated design chronology; challenge/answer separation on one host is not OS isolation.

The [full erratum](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/blob/08cf1ba38f6600d17370c8f4af8ee1f2dcaf3d4a/research/erna_v2/ERRATUM.md) provides the detail. The [separate post-hoc diagnostic](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/blob/08cf1ba38f6600d17370c8f4af8ee1f2dcaf3d4a/research/erna_v2/posthoc/README.md) concerns two identified recipes: approximately 3.7% under a fixed 153-independent-draw model. It is not the probability that luck caused the score gap, proof of seed robustness, or an exhaustive count of all matching recipes. The publication workflow did not repeat that Monte Carlo.

## Reproduction evidence and scope

The v2 source files `erna2.py`, `run_experiment.py`, `prereg.json` and `vendor/generic_solver.py`, and the 40 task blobs, match between the pinned release and the frozen v2 artifact checked on 14 November. The [reproduction receipt](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/blob/08cf1ba38f6600d17370c8f4af8ee1f2dcaf3d4a/research/erna_v2/evidence/reproduction_receipt.json) records replay of that frozen artifact: all three prediction files and all 120 decompressed trace payloads matched their originals byte for byte; gzip containers and host timings differ. All 184 original manifest entries matched. Eighteen packaged tests passed, subject to the vacuous-test limitation.

This is AI-assisted local reproduction, not independent human or official ARC validation. This supplement concerns the 40-task v2 probe; it does not independently validate the separate 26-output joint-constraints experiment described in the PR.

## Material input and licensing

The original implementation and fixtures were Claude-assisted; publication review and replay were OpenAI Codex-assisted, with additional AI source/rules reviews. Actual serving-model identity for the original configured Claude label was not independently established. No human line-by-line review or externally certified novelty is asserted. The solver invokes no LLM or network during inference.

The submitted pinned release retains its **MIT** code/documentation license and the bundled dataset's **Apache-2.0** license and attribution. The supplemental review snapshot has a separately scoped Apache-2.0 grant; it does not revoke or replace the pinned release's MIT grant. The `submission.yaml` code URL, version and score remain unchanged. V3 is separate and unfrozen.
