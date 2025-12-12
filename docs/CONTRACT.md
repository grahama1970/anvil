# Anvil System Contract (Draft)

## Overview

Anvil is a **no-vibes** debugging and hardening orchestrator. It guarantees that any debugging session follows a strict, verifyable process, producing structured artifacts at every step. This contract defines the boundaries of the system and the obligations of its components.

## 1. System Inputs

- **Target Repository**: A valid git repository root path.
- **Issue Description**: A textual description of the bug or task (via CLI arg or file).
- **Configuration**: `.dbg/tracks.yaml` defining parallel execution tracks (roles/providers).

## 2. System Outputs

All outputs are written to `.dbg/runs/<run_id>/`.

### 2.1 Core Artifacts

- **`CONTEXT.md`**: Relevant files and snippets extracted from the repo.
- **`REPRO.md`**: Plan to reproduce the issue (commands, expected vs actual).
- **`RUN_STATUS.json`**: Current state of the run (running, complete, failed).
- **`FILES.json`**: Index of files included in context.

### 2.2 Track Artifacts

Located in `.dbg/runs/<run_id>/tracks/<track_name>/`.

- **`iter_<NN>/ITERATION.json`**: Structured response from the provider (hypothesis, experiments, proposed changes).
- **`iter_<NN>/ITERATION.txt`**: Raw text output (redacted).
- **`iter_<NN>/PATCH.diff`**: (Optional) Unified diff proposed by the provider.

### 2.3 Verification & Decision

- **`VERIFY.md`**: Results of verification commands.
- **`SCORECARD.json`**: Automated scoring of each track.
- **`DECISION.md`**: Final decision on the winning track.

## 3. Invariants ("No Vibes")

1.  **Strict Schema Compliance**: All JSON artifacts must validate against their Pydantic schemas (defined in `src/anvil/artifacts/schemas.py`).
2.  **No Work Without Proof**: A track cannot claim to have fixed a bug without producing a `PATCH.diff` and passing self-reported checks.
3.  **Isolation**: Each track runs in a dedicated git worktree (`.dbg/worktrees/<run_id>/<track>`) to preventing cross-contamination.
4.  **Reproducibility**: `INIT` creates a `.dbg` folder with all necessary templates to re-run the session.
5.  **Optional Docker Isolation**: When run with `--docker`, verify commands execute in containerized environments for additional security.

## 4. Failure Modes

- **Disqualification**: If a track produces invalid JSON or fails to produce required artifacts, it is **disqualified** from the judging process.
- **System Crash**: If the orchestrator fails (e.g., git error), it writes a `CRASH.txt` log and sets `RUN_STATUS.json` to `FAIL`.

## 5. Directory Structure Contract

```text
.dbg/
├── tracks.yaml          # User config
├── runs/
│   └── <run_id>/
│       ├── CONTEXT.md
│       ├── REPRO.md
│       ├── RUN_STATUS.json
│       ├── tracks/
│       │   └── <track>/
│       │       └── iter_01/
│       │           ├── ITERATION.json
│       │           └── PATCH.diff
│       └── logs/        # Raw logs (captured stdout/stderr)
└── worktrees/
    └── <run_id>/
        └── <track>/     # Git worktree
```
