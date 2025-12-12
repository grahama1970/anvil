# Hardening Tasks — `anvil` (debugger harness)

This document provides a step-by-step hardening plan for a Gemini agent to follow.
Work through tasks in order. Each task is atomic and verifiable.

---

## Ground Rules (READ FIRST)

### 1. Contract Docstrings

**Every Python module must have a CONTRACT docstring** at the top that defines:

- **Inputs**: What the module receives
- **Outputs**: What artifacts/results it produces
- **Invariants**: What must always be true
- **Failure modes**: How errors are handled

Example pattern:

```python
"""Short description.

CONTRACT
- Inputs: ...
- Outputs (required): ...
- Outputs (optional): ...
- Invariants: ...
- Failure: ...
"""
```

### 2. CLI for Every Script

**Every module with meaningful logic must expose a `if __name__ == "__main__":` CLI** that:

- Parses minimal arguments (use `argparse` or `typer`)
- Demonstrates the module's core function
- Returns exit code 0 on success, non-zero on failure
- Prints results to stdout (or writes to specified output path)

Example pattern:

```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test <module>")
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    result = main_function(args.input)
    print(result)
```

### 3. Verification Commands

After each task, run these gates:

```bash
uv run ruff check .
uv run pytest
```

---

## Phase 1: Contract Docstrings

Add or improve CONTRACT docstrings in every module. Read the existing docstring first,
then enhance it to match the pattern above.

### Task 1.1: Core Modules

- [ ] `src/anvil/cli.py` — Add CONTRACT listing all subcommands and their args/outputs
- [ ] `src/anvil/config.py` — Add CONTRACT for YAML parsing and validation rules
- [ ] `src/anvil/orchestrator.py` — Add CONTRACT listing workflow steps and artifacts
- [ ] `src/anvil/doctor.py` — Add CONTRACT listing all checks and exit codes
- [ ] `src/anvil/init.py` — Add CONTRACT listing templates written
- [ ] `src/anvil/worktrees.py` — Add CONTRACT for worktree creation/cleanup

### Task 1.2: Steps

- [ ] `src/anvil/steps/base.py` — Add CONTRACT for Step protocol
- [ ] `src/anvil/steps/context_builder.py` — Enhance existing CONTRACT
- [ ] `src/anvil/steps/repro_plan.py` — Add/enhance CONTRACT
- [ ] `src/anvil/steps/track_iterate.py` — Enhance existing CONTRACT
- [ ] `src/anvil/steps/verify.py` — Enhance existing CONTRACT
- [ ] `src/anvil/steps/judge.py` — Enhance existing CONTRACT
- [ ] `src/anvil/steps/apply.py` — Enhance existing CONTRACT

### Task 1.3: Providers

- [ ] `src/anvil/providers/base.py` — Add CONTRACT for Provider protocol
- [ ] `src/anvil/providers/manual.py` — Add CONTRACT
- [ ] `src/anvil/providers/copilot_cli.py` — Enhance existing CONTRACT
- [ ] `src/anvil/providers/gemini_cli.py` — Enhance existing CONTRACT
- [ ] `src/anvil/providers/gh_cli.py` — Add CONTRACT (even for stub)

### Task 1.4: Utilities

- [ ] `src/anvil/util/ids.py` — Add CONTRACT for ID validation rules
- [ ] `src/anvil/util/shell.py` — Add CONTRACT for command execution
- [ ] `src/anvil/util/paths.py` — Add CONTRACT for path safety
- [ ] `src/anvil/util/redaction.py` — Add CONTRACT for redaction patterns
- [ ] `src/anvil/util/events.py` — Add CONTRACT for event logging
- [ ] `src/anvil/util/text.py` — Add CONTRACT

### Task 1.5: Artifacts & Collaboration

- [ ] `src/anvil/artifacts/store.py` — Add CONTRACT for path safety and write ops
- [ ] `src/anvil/artifacts/schemas.py` — Add CONTRACT listing all schemas
- [ ] `src/anvil/collab/blackboard.py` — Add CONTRACT
- [ ] `src/anvil/contracts/validate.py` — Add CONTRACT
- [ ] `src/anvil/contracts/base.py` — Add "future work" comment or remove placeholder
- [ ] `src/anvil/score/compute.py` — Add CONTRACT
- [ ] `src/anvil/prompts/load.py` — Add CONTRACT
- [ ] `src/anvil/treesitter_utils.py` — Add/enhance CONTRACT

---

## Phase 2: Per-Module CLIs

Add `if __name__ == "__main__":` CLI to each module. This enables direct testing
without going through the full orchestrator.

### Task 2.1: Utility CLIs

- [ ] `src/anvil/util/ids.py` — CLI: `--validate-run-id <id>` and `--new-run-id`
- [ ] `src/anvil/util/shell.py` — CLI: `--cmd <command> --cwd <dir>`
- [ ] `src/anvil/util/paths.py` — CLI: `--safe-filename <name>`
- [ ] `src/anvil/util/redaction.py` — CLI: `--redact <text>` or `--redact-file <path>`
- [ ] `src/anvil/util/events.py` — CLI: `--emit <json> --log-path <path>`

### Task 2.2: Step CLIs

- [ ] `src/anvil/steps/context_builder.py` — CLI: `--repo <path> --issue <text> --out-dir <path>`
- [ ] `src/anvil/steps/repro_plan.py` — CLI: `--issue <text> --out-dir <path>`
- [ ] `src/anvil/steps/verify.py` — CLI: `--repo <path> --out-dir <path>`
- [ ] `src/anvil/steps/judge.py` — CLI: `--run-dir <path> --tracks A,B`
- [ ] `src/anvil/steps/apply.py` — CLI: `--repo <path> --patch <path>`
- [ ] `src/anvil/steps/track_iterate.py` — CLI: `--run-dir <path> --track <name> --provider manual`

### Task 2.3: Provider CLIs

- [ ] `src/anvil/providers/manual.py` — CLI: `--track <name> --role <role> --out-dir <path>`
- [ ] `src/anvil/providers/copilot_cli.py` — CLI: `--prompt <text> --model <model>` (dry-run mode)
- [ ] `src/anvil/providers/gemini_cli.py` — CLI: `--prompt <text> --model <model>` (dry-run mode)

### Task 2.4: Artifact & Other CLIs

- [ ] `src/anvil/artifacts/store.py` — CLI: `--run-dir <path> --write <rel> --content <text>`
- [ ] `src/anvil/collab/blackboard.py` — CLI: `--run-dir <path> --tracks A,B`
- [ ] `src/anvil/score/compute.py` — CLI: `--run-dir <path> --tracks A,B`
- [ ] `src/anvil/prompts/load.py` — CLI: `--profile <name>` (prints profile content)
- [ ] `src/anvil/treesitter_utils.py` — CLI: `--file <path>` (prints outline)
- [ ] `src/anvil/config.py` — CLI: `--validate <tracks.yaml>`
- [ ] `src/anvil/worktrees.py` — CLI: `--repo <path> --create A,B` (dry-run mode)

---

## Phase 3: Bug Fixes (from REVIEW.md)

Fix bugs identified in REVIEW.md.

### Task 3.1: Resume Mode

- [ ] Read `src/anvil/cli.py` lines 202-220
- [ ] Read `src/anvil/orchestrator.py`
- [ ] Implement resume logic:
  - Load existing `RUN_STATUS.json` on resume
  - Skip completed steps based on artifact presence
  - Reload `issue_text` from existing `CONTEXT.md` or `RUN.json`
- [ ] Add test for resume functionality

### Task 3.2: Judge Scoring

- [ ] Read `src/anvil/steps/judge.py`
- [ ] Fix: Run verification per-worktree OR use per-track metrics from ITERATION.json
- [ ] Incorporate iteration `confidence` field into scoring
- [ ] Update scoring to differentiate tracks meaningfully
- [ ] Add test for judge scoring logic

### Task 3.3: Harden Session

- [ ] Read `src/anvil/orchestrator.py` `run_harden_session`
- [ ] Implement: Load tracks from `tracks.yaml`
- [ ] Implement: Run harden-specific workflow (breaker tracks, etc.)
- [ ] Add test for harden workflow

### Task 3.4: Provider Validation

- [ ] Read `src/anvil/config.py` `load_tracks_file`
- [ ] Add validation: Check `provider` value is in `{manual, copilot, gemini, gh_cli}`
- [ ] Fail fast with clear error message on unknown provider

### Task 3.5: Deprecated utcnow()

- [ ] Read `src/anvil/util/ids.py`
- [ ] Replace `datetime.datetime.utcnow()` with `datetime.datetime.now(datetime.UTC)`

### Task 3.6: Worktree Branch Conflict

- [ ] Read `src/anvil/worktrees.py`
- [ ] Fix: Detect existing `dbg/<run_id>/<track>` branches and either:
  - Refuse with clear error if `--run-id` conflicts, OR
  - Delete old branch + worktree before creating new one
- [ ] Add test for branch conflict handling

---

## Phase 4: Code Quality

### Task 4.1: Extract Provider Common Code

- [ ] Create `src/anvil/providers/common.py`
- [ ] Move shared functions from `copilot_cli.py` and `gemini_cli.py`:
  - `_between()`
  - `_normalize_iteration_json()`
  - `_build_prompt()`
- [ ] Update imports in both provider files
- [ ] Verify: `uv run ruff check .` and `uv run pytest`

### Task 4.2: Add --version Flag

- [ ] Read `src/anvil/cli.py`
- [ ] Add version callback using Typer's `typer.Option(callback=...)`
- [ ] Version should read from `debugger.__version__` or `importlib.metadata`

### Task 4.3: Add --force Flag to Init

- [ ] Read `src/anvil/init.py` and `src/anvil/cli.py`
- [ ] Add `--force` option to `dbg init` to overwrite existing templates

### Task 4.4: Improve Context Builder Regex

- [ ] Read `src/anvil/steps/context_builder.py` line 51
- [ ] Improve keyword extraction:
  - Lower minimum word length (e.g., 2 chars)
  - Consider TF-IDF or frequency-based selection
  - Handle hyphenated terms

### Task 4.5: Context Builder Safety

- [ ] Add file size cap (skip files > 1MB)
- [ ] Skip binary files (check first bytes for nulls)
- [ ] Ignore `.dbg/` and other generated directories

### Task 4.6: Redact ITERATION.json

- [ ] Read `src/anvil/steps/track_iterate.py`
- [ ] Apply redaction to `ITERATION.json` as well as `ITERATION.txt`
- [ ] Secrets may appear in JSON fields (hypothesis, experiments, etc.)

### Task 4.7: Apply Step Enhancement

- [ ] Read `src/anvil/steps/apply.py`
- [ ] Run `git apply --check` before actual apply
- [ ] Record clearer failure reason on mismatch

### Task 4.8: Add YAML Schema Validation

- [ ] Read `src/anvil/config.py`
- [ ] Use `jsonschema` to validate `tracks.yaml` structure
- [ ] Fail with clear schema error if invalid

### Task 4.9: Capture Provider stdout/stderr

- [ ] Read `src/anvil/providers/copilot_cli.py` and `gemini_cli.py`
- [ ] Write provider stdout/stderr to separate log files in track artifacts
- [ ] Helps debug provider failures

### Task 4.10: Verify Duration and Byte Counts

- [ ] Read `src/anvil/steps/verify.py` and `src/anvil/util/shell.py`
- [ ] Add `elapsed_s` and `stdout_bytes`/`stderr_bytes` to `verify.commands.json`
- [ ] Extend `CmdResult` to include elapsed time

### Task 4.11: EventLog Include run_id

- [ ] Read `src/anvil/util/events.py`
- [ ] Configure `EventLog` with `run_id` at construction
- [ ] Include `run_id` in every event automatically

---

## Phase 5: Test Coverage

### Task 5.1: Utility Tests

- [ ] Create `tests/test_ids.py` — test `validate_run_id`, `validate_track_name`, edge cases
- [ ] Create `tests/test_paths.py` — test `safe_filename`, path safety
- [ ] Create `tests/test_shell.py` — test `run_cmd` timeout, exit codes

### Task 5.2: Store Tests

- [ ] Create `tests/test_store.py` — test `ArtifactStore.path()` prevents path traversal
- [ ] Test symlink escape attempts

### Task 5.3: CLI Smoke Tests

- [ ] Create `tests/test_cli.py` — smoke tests for `dbg --help`, `dbg init --help`, etc.

### Task 5.4: Provider Tests

- [ ] Create `tests/test_providers.py` — test marker parsing, JSON normalization
- [ ] Test that provider failures are recorded in track artifacts (not crash)

### Task 5.5: Resource Tests

- [ ] Add test to `tests/test_schemas.py` — verify templates/profiles load via `importlib.resources`

### Task 5.6: Reachability Matrix Test

- [ ] Create `tests/test_reachability.py`
- [ ] Run `dbg debug run` with manual provider and verify expected artifacts:
  - `CONTEXT.md`, `FILES.json`
  - `REPRO.md`
  - `tracks/<track>/iter_01/ITERATION.json`, `ITERATION.txt`
  - `VERIFY.md`, `logs/verify.*.log`, `logs/verify.commands.json`
  - `DECISION.md`, `SCORECARD.json`

---

## Phase 6: Documentation

### Task 6.1: Fix README Accuracy

- [ ] Read `README.md` line 78 (tree-sitter section)
- [ ] Clarify that `debugger[treesitter]` only provides fallback
- [ ] Document `uv sync --group ast` for full tree-sitter support

### Task 6.2: Add End-to-End Example

- [ ] Add to README: complete example showing `dbg init` + `dbg debug run` + artifact inspection
- [ ] Show expected artifact structure

### Task 6.3: Document Trust Boundaries

- [ ] Add section to README or AGENTS.md explaining:
  - `shell=True` usage for verify commands
  - `.dbg/verify_contract.yaml` is trusted config
  - Security implications

### Task 6.4: Add gh_cli Provider Example

- [ ] Add README section showing `gh copilot` invocation wiring
- [ ] Document how to implement the gh_cli stub

### Task 6.5: Profile Documentation

- [ ] Read `src/anvil/prompts/profiles/*.md`
- [ ] Add "When to use" one-liner at top of each profile

### Task 6.6: AGENTS.md Improvement

- [ ] Add line: "If you are a human user, start here: README.md"
- [ ] Link to relevant README sections for non-agent users

---

## Phase 7: Docker Hardening

### Task 7.1: Dockerfile Improvements

- [ ] Read `Dockerfile`
- [ ] Add `ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1`
- [ ] Add non-root user (e.g., `RUN useradd -m appuser && USER appuser`)

### Task 7.2: Document Docker Provider Expectations

- [ ] Add to README: Docker image does NOT include copilot/gemini CLIs
- [ ] Document host-mount pattern for provider binaries if needed

---

## Phase 8: Final Verification

- [ ] Run `uv run ruff check .` — must pass
- [ ] Run `uv run pytest` — must pass
- [ ] Run `uv build` — must produce wheel
- [ ] Run `docker build -t debugger:local .` — must succeed
- [ ] Run `docker run --rm debugger:local --help` — must print help
- [ ] Test reachability matrix manually (run `dbg init` + `dbg debug run`)

---

## Completion Checklist

- [ ] All Phase 1 tasks complete (CONTRACT docstrings)
- [ ] All Phase 2 tasks complete (per-module CLIs)
- [ ] All Phase 3 tasks complete (bug fixes)
- [ ] All Phase 4 tasks complete (code quality)
- [ ] All Phase 5 tasks complete (test coverage)
- [ ] All Phase 6 tasks complete (documentation)
- [ ] All Phase 7 tasks complete (Docker hardening)
- [ ] All Phase 8 tasks complete (final verification)
