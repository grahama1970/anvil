# Bug: The `debug run` command should validate inputs before proceeding

## Problem

When running `anvil debug run`, if the `--issue` file doesn't exist, the command should fail with a clear error message rather than proceeding and crashing later.

Currently, if you run:

```bash
uv run python -m src.anvil.cli debug run --repo . --issue nonexistent.md --run-id test
```

The system starts processing and fails later when trying to read the file.

## Expected Behavior

1. If `--issue` points to a file that doesn't exist, exit immediately with:

   - Exit code 1
   - Error message: "Issue file not found: <path>"

2. Similarly, if `--tracks-file` is specified but doesn't exist, fail fast.

## Acceptance Criteria

1. Add validation in `cli.py` debug run command
2. Add test in `tests/test_cli.py` that verifies the error handling

## Files to Change

- `src/anvil/cli.py` - Add file existence check before calling orchestrator
- `tests/test_cli.py` - Add test for nonexistent issue file
