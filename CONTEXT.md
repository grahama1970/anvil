# Anvil Project Context

> Last Updated: 2025-12-13 | Tests: 52/52 passed

## What is Anvil?

Anvil is a **no-vibes debugging and hardening orchestrator** designed to be called by AI orchestrator agents. It runs parallel AI tracks to fix bugs or find vulnerabilities.
It is inspired by and achieves feature parity with [nicobailon/debug-mode](https://github.com/nicobailon/debug-mode).

## Two Core Modes

1. **Debug Mode**: Fix a known bug. Takes issue description, spawns parallel AI tracks (e.g. `backend_fixer`), picks winner via Judge.
2. **Harden Mode**: Proactively find vulnerabilities. Runs "breaker" tracks to discover bugs, missing tests, and generate patches.

## Current State

### ✅ Major Accomplishments (Copilot Critique Response)

Following a comprehensive code review by Copilot, the following **Critical** and **High Priority** issues were fixed in `9850d59`:

1.  **Worktree Isolation (Critical)**:
    - Providers now run in isolated worktrees (`.dbg/worktrees/<run_id>/<track>`), preventing file system contention between parallel tracks.
    - Updated `orchestrator.py` and `worktrees.py`.
2.  **API Stability (Critical)**:
    - Fixed `GeminiCliProvider` and `ClaudeCliProvider` crash (API signature mismatch for `normalize_iteration_json`).
3.  **Documentation (Critical)**:
    - Corrected clone URLs and added attribution to `debug-mode` in `README.md`.
4.  **Role-Aware Judge (High)**:
    - Judge now uses `TrackConfig` to detect roles.
    - Scoring logic updated: Fixers strictly penalized for missing patches; Breakers treated more leniently/encouraged.
5.  **Per-Iteration Verification (High)**:
    - `orchestrator` now opportunistically verifies patches per-iteration during the loop.
    - Generates `VERIFY.md` artifacts for the Judge to perform evidence-based scoring.
6.  **Harden Profile (High)**:
    - Externalized hardcoded prompts to `src/anvil/prompts/profiles/harden.md`.

### ✅ Feature Parity with `debug-mode`

- **Repro Modes**: Implemented `ReproAssess` step (`AUTO`, `SEMI_AUTO`, `MANUAL`).
- **Archive Branches**: Implemented `archive_branch()` for post-mortem analysis.

### What Works

- **Parallel Tracks**: Full isolation verified.
- **Provider Support**: Copilot, Gemini, Claude, Manual.
- **Judge**: Role-aware, evidence-based scoring.
- **Artifacts**: Strict schema enforcement for `ITERATION.json`, `VERIFY.md`, `SCORECARD.json`.

## Recent Changes (Previous Session)

1.  **Worktree Logic**: Expose `get_worktree_path(track)` public method.
2.  **Orchestrator**: Update `_process_track` to use worktree path and run verification.
3.  **Tests**: Added `tests/test_judge_role_aware.py` and `tests/test_repro_assess.py`.
4.  **Bug Fixes**: Restored missing diff extraction logic in providers.

## Production Ready (All Phases Complete)

The project is now considered **Production Ready** for autonomous agents.

### Key Features

1.  **Strict Contracts**: Documentation (`AGENT_ONBOARDING.md`) and validation (`anvil doctor`) enforced.
2.  **Robustness**: Worktrees fail hard if invalid; Cleanup is reliable; Docker propagated everywhere.
3.  **No Vibes**: Judge penalizes test failures (-100); Verification is deterministic.

### Verified Fixes

- **Worktree validation**: Fail clear if worktrees can't be created (Debug + Harden).
- **Robust patch cleanup**: `git reset --hard` + `git clean -fd` prevents contamination.
- **Docker propagation**: `--docker` applies to all verify steps.
- **Concurrency test**: Verified worktree path usage and parallel execution.
- **Auto-Cleanup**: Robust lifecycle management with `--no-cleanup` support.
- **CLI Cleanup**: `anvil cleanup` commands for manual management.
- **Doctor**: Enhanced health checks for providers and contract.
- **Harden Verify**: Per-iteration verification loop with `--verify-patches`.

## Commands to Verify

```bash
# Run all tests (all passing)
uv run pytest tests/ -v

# Run debug on itself (should use worktrees)
uv run python -m anvil.cli debug run --repo . --issue "Add missing test" --tracks-file dogfood/tracks.yaml

# Run harden on itself
uv run python -m anvil.cli harden run --repo .
```
