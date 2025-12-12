# Hardening Task: Implement Resume Mode (Task 3.1)

**Goal**: Implement proper resume logic in `src/anvil/orchestrator.py`.

**Current State**:

- `src/anvil/cli.py` has a `debug resume` command (lines 236-255)
- It sets `resume=True` in `RunConfig`
- The orchestrator `run_debug_session` receives this config but does NOT properly handle resume

**Requirements**:

1. Read `src/anvil/orchestrator.py` function `run_debug_session`
2. When `cfg.resume=True`:
   - Load existing `RUN.json` to get `issue_text` (don't require it in config)
   - Check which artifacts already exist (CONTEXT.md, REPRO.md, ITERATION.json files)
   - Skip completed steps based on artifact presence
   - Continue from the last incomplete iteration
3. Generate a patch that implements this logic

**Hints**:

- Check for `store.path("CONTEXT.md").exists()` to skip context building
- Check for `store.path("tracks", t.name, f"iter_{N:02d}", "ITERATION.json")` to find last iteration
- Load issue_text from `RUN.json` if `cfg.issue_text is None and cfg.resume`

**Success Criteria**:

- After implementation, running `dbg debug resume --run <existing_run_id>` should continue from where it left off
