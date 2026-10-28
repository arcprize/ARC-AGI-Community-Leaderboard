# MERENVAY–Mentova Runtime Repair

> **Methodology update — 11 October 2026.** The pinned upstream Mentova scorer contains an answer-conditioned search path: `Computed = TestOut` is checked before it accepts a candidate rule. Its archived **120/120** therefore remains a reproducible legacy result over **one selected test input per each of 120 public task IDs**, not the full ARC-AGI-2 multi-test metric. MERENVAY subsequently built a generic answer-isolated submission path that never receives expected test outputs. On the current official ARC-AGI-2 public evaluation data, that frozen pipeline produced a **94.027778% community-style task-average score** (mean of each task's fraction of solved test outputs), alongside **152/167 exact test outputs = 91.017964%** on an output-weighted/Kaggle-style calculation, with **105/120 task IDs** having all of their test outputs correct, in a GitHub-hosted regression run. A separate earlier first-candidate diagnostic also logged **120/120** first test inputs, zero failures, 20,026 ms. The underlying Mentova rule library was developed against these publicly known ARC tasks, so **none of these results measures genuine unseen-task generalisation or ARC Prize verification**. See the [public review discussion](https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/issues/1).

## Result reported

The current answer-isolated generic submission path, evaluated **after prediction artifacts were frozen**, produced:

- **94.027778% community-style task-average public score** — the comparator metric used by Noemon's published scorer
- **152/167 exact public test outputs = 91.017964%** — output-weighted/Kaggle-style
- **105/120 task IDs** with every public test output correct
- **120 task IDs / 167 test inputs** processed
- GitHub-hosted generation elapsed: **46.115 s** in run `38120350359` and **24.716 s** in independent rescore run `38124392038`; timing is environment/run dependent, not a speed record
- Submission SHA-256: `a9e169517a419a1ff9bb7613f2d44803a00825dc5820aa3058dcf4b331cf9199`

The earlier native runner remains preserved as a **legacy first-test-per-task reproduction**, not the full multi-test score:

- Windows x64 / SWI-Prolog 10.0.2 — run 1: **120/120 first test inputs**, 78.185 s, failures `[]`
- Windows x64 / SWI-Prolog 10.0.2 — run 2: **120/120 first test inputs**, 78.442 s, failures `[]`
- GitHub-hosted Ubuntu 24.04.5 / SWI-Prolog 9.0.4: **120/120 first test inputs**, 40.412 s, failures `[]`

## Contribution

The pinned upstream Mentova source is commit `d117c699416692cac7ceb951b09f2cdb484a89a6`.

The upstream dispatcher could reach correct, already-existing rules too late under its 10-second per-task limit. The MERENVAY patch moves six verified rules earlier using narrow O(cells) structural prefilters:

- `mirror_patch`
- `template_expand`
- `constellation`
- `mosaic_heal`
- `hole_color`
- `frame_compass`

The patch does **not** add answer keys, alter task data, or change transformation semantics. The contribution is a bounded runtime-stability and dispatch-order repair plus publicly recorded reproducibility runs. It is not a separate general-purpose ARC-solving system.

## Public evidence

- Code and reproduction instructions: https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction
- Full multi-test answer-isolated regression: https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/actions/runs/38120350359
- Independent rescore confirming both aggregate metrics: https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/actions/runs/38124392038
- Stable GitHub Actions run: https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/actions/runs/37769412232
- Evidence artifact: https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/actions/runs/37769412232/artifacts/11547158323
- GitHub SLSA/Sigstore attestation: https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/attestations/53909570
- Rekor transparency-log entry: https://search.sigstore.dev?logIndex=3147098838
- Detailed stable receipt: https://github.com/alnasserlegalservices/merenvay-arc2-public-reproduction/blob/main/STABLE_VERIFICATION_RECEIPT.md

The preserved **legacy first-test-per-task** GitHub-hosted workflow performs a clean checkout, pins the upstream commit, applies the public patch, executes one selected test input for each of the 120 public task IDs, asserts `RESULT score=120 total=120`, asserts `FAILS []`, uploads the evidence artifact and generates signed build provenance. This evidence supports only the legacy diagnostic, not the full multi-test score reported above.

## Evidence fingerprints

- GitHub artifact service digest: `sha256:da6a5d98a745c6f5fcad6d5a7a01b54f2b4e97f3c27279e8c873281ba7ead37b`
- Inner GitHub evidence ZIP SHA-256: `b79224b93df193dc9454be4b74eb5d3f1e752624c93291fbd8855cb1ee6f0bd1`
- GitHub run-log SHA-256: `cd4f2feb3b4a13584d2d8e482c4fb2b12d476e0920266e890d38369b7874e516`
- GitHub artifact patch SHA-256: `11a330022288ce124851d70488c0f7a1efe1351d109ea39d21c2e81d9aaa065c`
- Runner SHA-256: `46516f5efd776bb19eaec1f9004a412d85104ede657a3fe5b25a4d5fec35373e`

A final local stable evidence package was also timestamped through DigiCert RFC 3161:

- Evidence ZIP SHA-256: `5aab73ee0d7bc5c53430ebfa0565b75c29206815c394792d9c4b31925c46b59f`
- Timestamp: `2026-10-08 11:24:23 GMT`
- Status: `Granted`
- Local cryptographic verification: `Verification: OK`

## Important limitations

This is a **self-reported public-evaluation result** submitted for transparent community review. It is not an ARC Prize Verified semi-private or private score, does not establish hidden-set generalisation, and is not a certificate of general intelligence.

The underlying Mentova solver was developed task-by-task against the public evaluation corpus and its published report discloses human solution walkthroughs and official-answer confirmation for difficult public tasks. Accordingly, this entry should be interpreted as a reproducible symbolic public-benchmark implementation and runtime-repair record—not as uncontaminated evidence of fluid intelligence on unseen tasks.

The original upstream evaluation procedure used test outputs inside rule search. The earlier answer-isolated first-candidate diagnostic did not pass the expected test output into prediction, but it covered only one selected test input per task ID. The newer generic answer-isolated path covers every current public test input and scores **94.027778% on the community-style task-average metric**, with **152/167 = 91.017964% output-weighted**, after predictions are frozen. This addresses the measurement leak and the earlier incomplete multi-test accounting, but **not** benchmark exposure or rule-set overfitting. All outcomes are described for transparency, not as proof of hidden-set generalisation or ARC Prize verification.
