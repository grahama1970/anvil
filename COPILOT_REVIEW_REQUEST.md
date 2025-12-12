# Asyncio Conversion and Multi-Iteration Loops

## Repository and branch

- **Repo:** `grahama1970/anvil` (or current repo)
- **Branch:** `main` (or current branch)
- **Paths of interest:**
  - `src/anvil/orchestrator.py`
  - `src/anvil/providers/base.py`
  - `src/anvil/providers/copilot_cli.py`
  - `src/anvil/providers/gemini_cli.py`
  - `src/anvil/cli.py`
  - `tests/test_loop_logic.py`

## Summary

I have converted the core execution engine of Anvil from synchronous `subprocess` calls to asynchronous `asyncio` execution. This enables running multiple provider tracks (e.g., Copilot and Gemini) concurrently. I have also implemented autonomous multi-iteration loops, allowing tracks to self-correct over multiple turns until `max_iters` is reached or a `DONE` signal is received.

## Objectives

### 1. Asyncio Execution

- Verify that `asyncio.gather` in `orchestrator.py` correctly handles concurrent track execution.
- Review `CopilotCliProvider` and `GeminiCliProvider` for correct usage of `asyncio.create_subprocess_exec` (ensure pipes are managed, timeouts handled).
- Check that the `Provider` protocol properly defines `async def run_iteration`.

### 2. Multi-Iteration Loops

- Review the `_process_track` logic in `orchestrator.py` for the iteration loop:
  - Is `max_iters` respected?
  - Does the `status_signal: DONE` check correctly break the loop?
  - Is `BLACKBOARD.md` correctly updated and read safely (race conditions accepted)?

### 3. Error Handling

- Ensure exceptions in one track do not crash the entire orchestrator (handled by `asyncio.gather` exception propagation vs try/except blocks inside `_process_track`).
- Review `_ErrorProvider` usage and async compatibility.

## Clarifying questions

1. **Race Conditions:** Is the current "last write wins" / "read fresh" strategy for `BLACKBOARD.md` acceptable for the MVP, or do we need strict locking (e.g. `asyncio.Lock`)?
2. **Signal Handling:** Should `SIGINT` (Ctrl+C) be handled explicitly to graceful shutdown subprocesses?

## Deliverable

Reply with:

- **Code Review Comments:** Identify bugs, race conditions, or improvements.
- **Suggestions:** specifically for robust error handling in `asyncio.gather`.
