# Comprehensive Code Review Request: Anvil Orchestrator

## Repository and branch

- **Repo:** `grahama1970/anvil`
- **Branch:** `main`
- **Paths of interest:**
  - `src/anvil/orchestrator.py` (main orchestration logic)
  - `src/anvil/steps/track_iterate.py` (provider iteration + validation)
  - `src/anvil/steps/judge.py` (winner selection)
  - `src/anvil/providers/common.py` (prompt building + JSON normalization)
  - `src/anvil/artifacts/schemas.py` (Pydantic models)
  - `src/anvil/collab/blackboard.py` (cross-track observations)

## Summary

Anvil is a **no-vibes debugging and hardening orchestrator**. It spawns parallel AI tracks to fix bugs or find vulnerabilities, using artifact-backed scoring to pick winners. The project has two core modes:

1. **Debug mode**: Fix a known bug with parallel tracks, judging, and auto-apply
2. **Harden mode**: Proactively find vulnerabilities with breaker tracks

**Current state:** 44/44 tests passing, both modes functional.

**Request:** Perform a comprehensive code review focusing on correctness, edge cases, error handling, and architectural concerns.

## Objectives

### 1. Orchestrator review (`orchestrator.py`)

- Review `run_debug_session()` (~250 lines) for:

  - Correct parallel track execution with `asyncio.gather()`
  - Resume logic when `cfg.resume=True`
  - Proper disqualification handling
  - Edge cases in winner selection and auto-apply

- Review `run_harden_session()` (~200 lines) for:
  - Breaker track execution correctness
  - HARDEN.md report generation
  - Blackboard update timing

### 2. Validation chain review

In `track_iterate.py`:

- Is `IterationEnvelope.model_validate()` sufficient for schema enforcement?
- What happens if provider returns malformed JSON that json_repair can't fix?
- Is exit code 2 the right signal for schema failures?

In `common.py`:

- Review `normalize_iteration_json()` fallback behavior
- Is `json_repair` properly integrated?
- Can malformed LLM output cause silent data loss?

### 3. Judging logic review (`judge.py`)

- Review scoring formula: confidence + patch presence + verification
- Is the "positive score required to win" rule correct?
- Should disqualified tracks affect the scoring of others?
- Edge case: What if all tracks have score ≤ 0?

### 4. Provider abstraction review

- Are all providers correctly implementing the `Provider` protocol?
- Is the `_ErrorProvider` fallback a good pattern?
- Review timeout handling across copilot/gemini/claude providers

### 5. Blackboard correctness (`blackboard.py`)

- Does `build()` correctly extract observations from latest iteration?
- Is `write()` idempotent?
- What happens if a track has no iterations?

## Constraints for review

- Focus on **correctness** and **edge cases**, not style/formatting
- Identify any **silent failures** where errors are swallowed
- Flag any **race conditions** in the parallel track execution
- Note any **contract violations** (see CONTRACT docstrings in each file)
- Prioritize findings by severity: Critical > High > Medium > Low

## Acceptance criteria for a "clean" codebase

1. All async operations properly awaited
2. All file I/O has explicit encoding
3. No bare `except:` clauses that swallow errors
4. Schema validation failures cause track disqualification
5. Crash artifacts written when exceptions occur
6. Resume logic doesn't lose progress or repeat work

## Known concerns

1. **Harden mode directions:** Currently hardcoded in `run_harden_session()`. Should these be configurable?

2. **Blackboard race condition:** Parallel tracks call `Blackboard().write()` which reads all tracks. Could this cause issues?

3. **Validation leniency:** `normalize_iteration_json()` adds defaults for missing fields. Is this too lenient?

4. **TrackIterate parameters:** Recently added `directions_text` as optional param. Is the signature clean?

## Clarifying questions

_Answer inline here or authorize assumptions:_

1. **Scoring weights:** Current formula weights confidence (from LLM) + 10pts for patch + 40pts for VERIFY PASS. Is this balance correct?

2. **Disqualification threshold:** Any non-zero exit from `check()` disqualifies. Should there be a warning-only tier?

3. **HARDEN.md format:** Is the current report format useful? Should it include more structure (JSON sibling)?

4. **Provider timeouts:** All providers default to 600s timeout. Is this appropriate for all models?

5. **Resume granularity:** Currently resume checks per-track iteration existence. Should it be more granular?

## Touch points for review

| File               | Functions                                                                             | Lines |
| ------------------ | ------------------------------------------------------------------------------------- | ----- |
| `orchestrator.py`  | `run_debug_session`, `run_harden_session`, `_process_track`, `_process_breaker_track` | ~400  |
| `track_iterate.py` | `run`, `check`                                                                        | ~100  |
| `judge.py`         | `run`, `check`                                                                        | ~120  |
| `common.py`        | `normalize_iteration_json`, `build_prompt`, `extract_between`                         | ~150  |
| `blackboard.py`    | `build`, `write`                                                                      | ~70   |
| `schemas.py`       | `IterationEnvelope`, `validate_iteration_json`                                        | ~50   |

## Deliverable

Reply with:

1. **Critical findings** (must fix before production)
2. **High-priority findings** (should fix soon)
3. **Medium-priority findings** (nice to have)
4. **Answers to clarifying questions**
5. **Suggested architectural improvements** (if any)

Format as numbered lists with file:line references where applicable.

## Verification commands

```bash
# Run all tests
uv run pytest tests/ -v

# Test harden mode
uv run python -m anvil.cli harden run --repo . --artifacts-dir /tmp/anvil-harden

# Test debug mode with manual provider
uv run python -m anvil.cli debug run --repo . --issue "Test issue" --artifacts-dir /tmp/anvil-debug

# Check CLI help
uv run python -m anvil.cli --help
```
