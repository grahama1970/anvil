# Agent Onboarding Guide

> [!IMPORTANT]
> This guide is for AI Agents (e.g., Sparta, Auto-Dev) integrating Anvil.
> Humans should read `QUICKSTART.md`.

## Prerequisites

Before invoking Anvil, ensure your environment meets these strict requirements:

1.  **Git Repository**: The target directory **MUST** be a valid git repository.
    - Check: `git -C <target_dir> rev-parse --is-inside-work-tree` (Exit code 0)
    - **Failure to ensure this will cause Anvil to fail hard.**
2.  **Dependencies**: `python 3.10+`, `git`.
3.  **Docker (Recommended)**: For robust verification.
    - Check: `docker info` (Exit code 0)
    - If available, set `ANVIL_DOCKER_DEFAULT=1` env var or pass `--docker`.

## Setup Checklist

1.  **Installation**:
    ```bash
    pip install anvil-harness
    ```
2.  **Initialization**:
    ```bash
    cd /path/to/target/repo
    anvil init
    ```
3.  **Validation**:
    ```bash
    anvil doctor
    ```
    **CONTRACT**: You MUST run `anvil doctor` before starting sessions. If it fails, do not proceed.

## Usage Patterns

### Debug Mode (Fix a Bug)

**Goal**: Given an issue description, produce a verified patch.

```bash
anvil debug run \
  --repo /path/to/repo \
  --issue "Login button throws 500 error on click" \
  --run-id <unique-agent-run-id>
```

**Output Contract:**

- **Success**: Exit code 0, status `OK` or `DONE`.
- **Artifacts**: Check `.dbg/runs/<run_id>/DECISION.md` for the chosen patch.
- **Patches**: Located in `.dbg/runs/<run_id>/tracks/<winner_track>/iter_<XX>/PATCH.diff`.

### Harden Mode (Red Teaming)

**Goal**: Proactively find vulnerabilities or bugs.

```bash
anvil harden run \
  --repo /path/to/repo \
  --run-id <unique-agent-run-id>
```

**Output Contract:**

- **Findings**: Check `.dbg/runs/<run_id>/HARDEN.md`.
- **Structured Data**: Parse `.dbg/runs/<run_id>/RUN_STATUS.json`.

## Strict Contracts

Anvil operates on "No Vibes" principles. Agents must adhere to these contracts:

### 1. Verification Contract

- **PASS** means the verification command (e.g., `pytest`) returned exit code 0.
- **PASS with No Tests** is a failure. Anvil checks for this.
- **Docker**: Always prefer docker execution for true signal.

### 2. Artifact Location Contract

All artifacts are strictly located at:

- Root: `.dbg/runs/<run_id>/`
- Status: `.dbg/runs/<run_id>/RUN_STATUS.json`
- Track Artifacts: `.dbg/runs/<run_id>/tracks/<track_name>/`

### 3. Failure Handling

If Anvil returns `FAIL`:

1.  **Check `CRASH.txt`**: Located in run root.
2.  **Worktree Validation**: If error is "Worktree validation failed":
    - Run: `anvil cleanup run --run-id <run_id>`
    - Retry the run.
3.  **Git Errors**: Ensure repo is clean before starting.

## Troubleshooting

### "Worktree validation failed"

- **Cause**: Stale branches from previous crashed runs or non-git repo.
- **Fix**:
  ```bash
  anvil cleanup run --run-id <current_run_id>
  # OR clean everything
  anvil cleanup all
  ```

### "Context check failed"

- **Cause**: Repo too large or missing critical files.
- **Fix**: Reduce scope or check repo permissions.

### "Repo is not a git repository"

- **Cause**: Target directory missing `.git`.
- **Fix**: Initialize git or fix path.
