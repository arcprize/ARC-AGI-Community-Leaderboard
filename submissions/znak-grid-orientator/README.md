# ZNAK Grid Orientator — submission scope and provenance

## Current Community submission

This submission covers the public ARC-AGI-1 and ARC-AGI-2 method and the recorded
version 1.0 results in `submission.yaml`. Those results remain self-reported
local public-evaluation results, not ARC Prize Verified or Kaggle hidden-set
results. The linked public code describes the recorded GPT-5.6 Sol runs.

## Correction to the earlier ARC-AGI-3 entry

The earlier version 1.1 ARC-AGI-3 score association has been withdrawn from the
active benchmark claims in this submission after a provenance review. This is
our correction of the submission scope, not an organizer disqualification.

[Public scorecard C144](https://arcprize.org/scorecards/2e350e76-52d8-4e10-96de-39aff7405567)
was observed on 2026-10-13 displaying 99.69%, 183/183 levels, 25/25 environments,
and 6564 actions. The card and the previous commits are preserved as historical
evidence.

The inspected C144 runner played back previously recorded action sequences,
including public-reference-derived routes. It did not call MAI-Thinking-1 or
another LLM in that playback loop. The upstream provenance of the routes is
mixed or unresolved; some records have conflicting independent/reference-derived
qualifiers. We do not claim that all routes were independently discovered.

The previous metadata attributed C144 to MAI-Thinking-1, but that connection
has not been established. A separate MAI experiment is not evidence that MAI
produced this card. The card is retained as a public route-reproduction artifact,
not submitted here as evidence of general-purpose solving of new ARC-AGI-3 games.

Competition Mode for this historical card is unconfirmed. The inspected open
request supplies tags and opaque metadata without `competition_mode: true`;
the retained close/public data does not provide a confirming mode field.
Direct REST can enable Competition Mode using that documented field; importing
the Python SDK is not itself the eligibility test. No tag or retrospective
metadata change is treated as proof of the original mode.

A future ARC-AGI-3 submission would need its own reproducible public producer,
resolved route/data provenance, and a properly evidenced Competition Mode run.
No new game, scorecard or model run was performed for this correction.

References:
- [Community review criteria](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/blob/main/README.md#what-belongs-here)
- [ARC-AGI-3 submission requirements](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/blob/main/CONTRIBUTING.md#required-fields)
- [REST Competition Mode field](https://docs.arcprize.org/api-reference/scorecards/open-scorecard#body-competition-mode)

