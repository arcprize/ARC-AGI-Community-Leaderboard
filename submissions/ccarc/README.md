# CCARC: how the ARC-AGI-3 result was produced

Code: [dastin359/CCARC](https://github.com/dastin359/CCARC), version 0.2.0 (commit `ca9b96e`, 2026-09-04).

## The runs

Each of the 25 public games was played live on its own competition-mode
scorecard (2026-08-30/31), with the same setup for every game:

- Claude Code with Claude Opus 5 at effort `high`;
- an action cap of 5x the game's human-baseline total; baselines withheld from the solver;
- a wall clock of 3 h (13 games) or 8 h (12 games);
- the solver confined by the harness's mount and network namespaces, reaching the
  game only through the ARC proxy;
- the generic solver prompt only: no game-specific text, and no operator input to
  a running solver.

A play cut short by an infrastructure problem (an account's 5-hour usage limit,
an orchestrator bug) was played again from the start; sk48's first two plays
were disrupted this way, and its third is the one on the card. No play was
chosen over another by its score.

## The scorecard

The orchestrator logged every action of every run. After the sweep it replayed
the 25 logged runs, in order, onto one fresh competition-mode scorecard
(7fb310c1, 2026-09-01) and closed it. 21 actions missing from the logs were
restored from the proxy log and 8 could not be recovered, so the card holds 7,809
of the 7,817 actions played live. Every action and frame on the card is public:
each game on the scorecard page has "Watch replay" and "Download recording".

## Code

The runs were played on the development tree that 0.2.0 was cut from. 0.2.0
leaves the solver prompt files and doctrine unchanged, and changes no ARC-AGI-3
guardrail. It differs in:

- names and comments, and the wording of two ARC-AGI-2 toolkit sentences the
  solver sees;
- defaults: the action cap is now 5x (the value used); the wall clock defaults to
  8 h; re-prompting a stopped solver is on only when `CCARC3_MAX_NUDGES` is set;
- tooling left out of the release: the sweep orchestrator, the replay tool, the
  scoring module and a test bench;
- ARC-AGI-2 only: per-driver staging, which keeps the dataset loader off the
  ARC-AGI-2 solver's import path, was added for the release.

To run a game with 0.2.0, see "Running an ARC-AGI-3 game" in the CCARC README.
