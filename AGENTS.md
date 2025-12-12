# AGENTS.md — Rules of the Debugger Game (No Vibes)

This project is designed to be run by humans *and* orchestrator agents.

## Top-level features
- `dbg debug`: solve a specific issue from an issue-like prompt
- `dbg harden`: red-team a repo or candidate patch

## Contracts are law
Every step has:
- a **docstring CONTRACT** (executable unit),
- and a per-worktree **CONTRACT.md** (workflow unit).

### Disqualification (hard fail)
A track/iteration is DISQUALIFIED if it:
1) **Drifts a contract** (breaks required artifact schema, missing required outputs, unversioned interface changes).
2) **Does not run required `check` gates** for the steps it touched (or cannot produce command logs/exit codes).
3) **Does not produce required artifacts** (e.g., ITERATION.json, PATCH.diff if claiming a fix, verify logs if claiming verified).
4) **Claims success without artifacts** (e.g., “tests passed” without verify logs).
5) **Edits outside its worktree** or forbidden paths.

DISQUALIFIED candidates may not win judging.

### Soft failures (recoverable with penalty)
Transient tool failures (timeouts/rate limits) may be retried *once* within the same iteration budget.

## “No claim without an artifact”
Every statement of progress must reference an artifact:
- command logs
- test output
- repro logs
- diffs

## Collaboration
Collaboration is allowed only via the orchestrator-managed blackboard:
- default: observations-only (no full patch sharing)
- artifacts: `BLACKBOARD.json` / `BLACKBOARD.md`

## Verification
Verification is a contract:
- you do not “verify” by narration
- you verify by running commands listed in the verify contract and storing logs

## Scoring
Scores are computed by the harness from artifacts, not authored by agents.
