# Contributing to the ARC Prize Community Leaderboard

Thanks for submitting your work!

## Submitting a New Entry

1. **Fork** this repository
2. **Create a new directory** under `submissions/` with a unique, lowercase, hyphenated ID:
   ```
   submissions/my-method-name/
   ```
3. **Add a `submission.yaml`** file in your directory. Copy the template from `submissions/.example/submission.yaml` and fill in your details.
4. **Open a Pull Request** against the `main` branch.

### What Happens Next

- Automated checks will run on your PR to validate formatting, required fields, and summarize your submission.
- If checks fail, review the error messages and push fixes to your PR branch.
- A maintainer reviews passing PRs on a roughly weekly cadence.
- Once merged, your entry appears on the leaderboard.

## Updating an Existing Entry

To update your submission (e.g. improved score, new version):

1. Add a new entry to the `versions` list in your existing `submission.yaml`
2. Open a PR with the changes

Do **not** create a new directory for updates - keep everything in your original submission directory.

## Submission Requirements

### Required Fields

- `name` - unique display name for your method
- `authors` - at least one author. Each author needs a `name` and at least one link (`url`, `twitter`, `linkedin`, `scholar`, or `github`)
- `description` - brief explanation of your approach
- `code_url` - link to a **public** repository
- `versions` - at least one version entry with:
  - `version` - version string
  - `date` - date in YYYY-MM-DD format
  - `models` - at least one model with `name`
  - `scores` - a list of score objects. Fields differ by benchmark:

    **arc-agi-1 and arc-agi-2:**
    - `benchmark` - `"arc-agi-1"` or `"arc-agi-2"`
    - `score` - **required**; number 0-100
    - `set` - **required**; eval set used (e.g. `"public"`, `"semi-private"`, `"private"`)
    - `cost` - optional; USD cost to achieve score (positive number)
    - `scorecard_url` - **not allowed**; scorecards are only available for arc-agi-3

    **arc-agi-3:**
    - `benchmark` - `"arc-agi-3"`
    - `scorecard_url` - **required**; link to your scorecard on `arcprize.org`. arc-agi-3 scores are pulled automatically from the scorecard and should not be self-reported. Your scorecard must be generated using **Competition Mode** (`OperationMode.COMPETITION`) - see the [ARC docs](https://docs.arcprize.org/toolkit/competition_mode) for details.
    - `set` - **required**; eval set used (e.g. `"public"`, `"preview"`)
    - `cost` - optional; USD cost to achieve score (positive number)
    - `score` - **not allowed**; do not include a numeric score for arc-agi-3 entries

  Using a list allows multiple entries for the same benchmark (e.g. different sets or cost tiers). Example:
  ```yaml
  scores:
    - benchmark: "arc-agi-2"
      score: 62.3
      set: "public"
      cost: 1.50
    - benchmark: "arc-agi-2"
      score: 45.0
      set: "semi-private"
      cost: 1.50
    - benchmark: "arc-agi-3"
      scorecard_url: "https://arcprize.org/scorecards/your-scorecard-id"
      set: "preview"
      cost: 8.50
  ```

### Optional Fields

- `citation` - how to reference your work
- `paper_url` - link to a paper (must resolve if provided)
- `twitter_url` - link to a tweet or thread (must resolve if provided)

### Guidelines

- Your `code_url` must point to a **public** repository at the time of submission.
- You may include additional files in your submission directory (READMEs, diagrams, etc.) but please keep it lightweight - no binaries, model weights, or large data files. Link to those instead.
- arc-agi-1/arc-agi-2 scores are self-reported. Misrepresenting results may result in your entry being removed.
- arc-agi-3 scores are pulled automatically from your scorecard - do not self-report a numeric score.
- Be respectful in discussions and PR comments.

## Directory Structure

```
submissions/
  .example/
    submission.yaml        # Template - copy this
  my-method-name/
    submission.yaml        # Your submission
    README.md              # Optional: extra detail about your method
  another-method/
    submission.yaml
```

## Review Criteria

Every submission is judged against the three bars in the README's [What Belongs Here](README.md#what-belongs-here): general-purpose, an open system (not just the output), and a novel contribution. We judge the *method*, not the score - see [About scores](README.md#about-scores) for why self-reported numbers aren't displayed.

Beyond that, a submission must:

- Pass all automated checks
- Be a genuine submission (not spam, not obviously fake)
- Link to a **public** code repository
- Include a clear description of the method

We don't verify scores or run your code. ARC Prize may choose to verify submissions independently at a later time, but the default is that we do not.

## Questions?

Ask in the [ARC Prize Discord](https://discord.com/invite/9b77dPAmcA).
