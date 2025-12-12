# Project Review (anvil / `debugger`)

This repo is a small, contract-driven “debug/harden” harness designed to be imported into other git
repos and emit artifact-backed runs under `.dbg/runs/<run_id>/`.

## Build + Deploy Status (verified)

- Local env:
  - `uv venv --python=3.11.12 .venv`
  - `uv sync` (installs `dependency-groups.dev`)
  - `uv sync --group ast` (installs `treesitter-tools` from `file:///home/graham/workspace/experiments/treesitter-tools`)
- Gates:
  - `uv run ruff check .`
  - `uv run pytest`
  - `uv build`
- Docker:
  - `docker build -t debugger:local .`
  - `docker run --rm debugger:local --help`

## Top-level files

### `AGENTS.md`
- Good: makes the contract expectations explicit (“no claim without artifact”).
- Risk: reads like a judging harness spec; consider linking to README sections for normal users.
- Suggestion: add a short “If you are a human user, start here: README.md” line at the top.

### `pyproject.toml`
- Good: clean dependency set, src-layout packaging, `dbg` entrypoint.
- Good: `dependency-groups.dev` makes local checks (`pytest`, `ruff`) reproducible under `uv`.
- Note: `dependency-groups.ast` is intentionally workstation-specific (absolute `file:///...` path).
  Keep it optional (as it is now) to avoid breaking “normal” installs.

### `uv.lock`
- Good: enables `uv sync --frozen` and a deterministic Docker build.
- Note: if you intend to publish to PyPI, keep the lock anyway (it’s for deploys, not publishing).

### `Dockerfile`
- Good: pinned to `python:3.11.12-slim` and pins `uv==0.7.10`.
- Good: uses `uv.lock` + `--frozen` + `--no-dev` for small runtime images.
- Suggestion: consider adding `ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1`.
- Suggestion: optionally run as a non-root user if you’ll run this container in shared environments.

### `.dockerignore`
- Good: excludes venv/caches/tests to keep the image context small.
- Note: if you ever want to run unit tests inside Docker, remove `tests/` from this ignore file.

### `.gitignore`
- Good: ignores venv/caches/build artifacts and `.dbg/` runs.

### `.python-version`
- Good: documents the intended interpreter (`3.11.12`) for tools like `pyenv`.

### `README.md`
- Good: explains the workflow and commands clearly.
- Improvement made: removed hardcoded `cd debugger` so it works regardless of repo folder name.
- Suggestion: add a concrete end-to-end example showing `dbg init` + a sample `dbg debug run`.

## `src/debugger` package

### `src/debugger/__init__.py`
- Good: exports a small public surface (`RunConfig`, `TrackConfig`, `run_*_session`).
- Suggestion: consider exporting `dbg` CLI less, and keep CLI under `cli.py` only (already true).

### `src/debugger/cli.py`
- Good: Typer layout is straightforward (`dbg debug ...`, `dbg harden ...`).
- Fix applied: removed Ruff `B008` issues by hoisting `typer.Option(...)` to module-level constants.
- Fix applied: validates `run_id`/`candidate_run` and `candidate_track` to avoid path/branch injection.
- Suggestion: add `--version` command/option (Typer supports this) for easier support/debugging.

### `src/debugger/config.py`
- Good: minimal YAML-driven configuration model (tracks/policy/collab/context).
- Fix applied: validates track names on load (prevents invalid branch/path names later).
- Suggestion: consider schema validation for the YAML itself (you already ship `jsonschema`).

### `src/debugger/doctor.py`
- Good: checks presence of `git`, `docker`, `rg`, `gh` and whether target is a git repo.
- Note: currently marks non-git repo as `FAIL` (exit 2). That’s fine if you *require* git worktrees.

### `src/debugger/init.py`
- Good: writes `.dbg/` templates without clobbering existing files.
- Suggestion: add a `--force` option to overwrite templates intentionally.

### `src/debugger/orchestrator.py`
- Good: linear, readable workflow; emits core run artifacts (`RUN.json`, `RUN_STATUS.json`, etc.).
- Fix applied: crash-guard writes `CRASH.txt` and sets `RUN_STATUS.json` to `FAIL` on exceptions.
- Fix applied: provider selection is now wired (`manual`, `copilot`, `gemini`, `gh_cli`) and per-track model
  selection works via `tracks.yaml`.

### `src/debugger/worktrees.py`
- Good: worktree layout and branch naming are deterministic per run.
- Fix applied: “best effort” now truly best effort (non-git repos skip creation instead of raising).
- Suggestion: write a small artifact log when skipping worktrees, for better auditability.

### `src/debugger/treesitter_utils.py`
- Good: optional dependency behavior (“no raise, return []”) matches contract.
- Fix applied: prefers `treesitter-tools` (if installed) and falls back to `tree_sitter_languages`.
- Suggestion: add language/extension coverage gradually; keep returning stable schemas.

## Artifacts

### `src/debugger/artifacts/__init__.py`
- Empty marker file; ok.

### `src/debugger/artifacts/schemas.py`
- Good: Pydantic models define the core artifact shapes.
- Suggestion: consider tighter typing for `experiments` / `proposed_changes` if consumers depend on it.

### `src/debugger/artifacts/store.py`
- Good: centralized artifact IO.
- Fix applied: hardened `path()` to prevent writing outside `run_dir` (path traversal / symlink escapes).
- Suggestion: add a helper to write “command logs + exit code” as a single JSON record.

## Collaboration

### `src/debugger/collab/__init__.py`
- Empty marker file; ok.

### `src/debugger/collab/blackboard.py`
- Good: observations-only extraction aligns with AGENTS.md rules.
- Suggestion: sanitize/normalize `experiments` fields (they’re untyped right now).

## Contracts

### `src/debugger/contracts/__init__.py`
- Empty marker file; ok.

### `src/debugger/contracts/base.py`
- Placeholder; ok.
- Suggestion: either remove until used or add a tiny “future work” comment on intended direction.

### `src/debugger/contracts/validate.py`
- Good: simple required-artifacts check that produces a `CheckResult`.
- Suggestion: add optional schema validation hooks for JSON/YAML artifacts.

## Prompts

### `src/debugger/prompts/__init__.py`
- Empty marker file; ok.

### `src/debugger/prompts/load.py`
- Good: profiles are packaged resources, so it works from wheels.
- Suggestion: handle missing profiles with a clearer error message listing available ones.

### `src/debugger/prompts/profiles/__init__.py`
- Empty marker file; ok.

### `src/debugger/prompts/profiles/*.md`
- Good: crisp “no vibes” operational profiles.
- Suggestion: add a short “when to use” note per profile (one sentence at top).

## Providers

### `src/debugger/providers/__init__.py`
- Empty marker file; ok.

### `src/debugger/providers/base.py`
- Good: small Provider protocol and a single ProviderResult shape.
- Fix applied: `ProviderResult.meta` now defaults to an empty dict (no `None`/type-ignore).

### `src/debugger/providers/manual.py`
- Good: offline/manual mode is useful and safe by default (no patch application).
- Suggestion: consider emitting a `status_signal` like `NEEDS_MORE_WORK` for manual templates.

### `src/debugger/providers/gh_cli.py`
- Good: explicit stub (doesn’t pretend to call a model).
- Suggestion: add a README section showing one example invocation wiring (`gh copilot` or similar).

### `src/debugger/providers/copilot_cli.py`
- Good: enables per-track `copilot --model ...` selection (e.g. `claude-sonnet-4.5` vs `gpt-5`).
- Note: parsing is intentionally strict (marker-based) to avoid ambiguous output.
- Suggestion: consider capturing provider stdout/stderr to separate log artifacts in the future.

### `src/debugger/providers/gemini_cli.py`
- Good: enables per-track `gemini --model ...` selection (e.g. `gemini-3-pro`).
- Note: depends on local Gemini CLI auth/config; failures are recorded in track artifacts.

## Scoring

### `src/debugger/score/__init__.py`
- Empty marker file; ok.

### `src/debugger/score/compute.py`
- Good: artifact-backed scoring; simple and transparent.
- Suggestion: keep score computation deterministic and document the rubric in `judge_blind_rubric.md`.

## Steps

### `src/debugger/steps/__init__.py`
- Empty marker file; ok.

### `src/debugger/steps/base.py`
- Good: Protocol gives a consistent `run/check` contract.

### `src/debugger/steps/context_builder.py`
- Good: produces `FILES.json` and a human-readable `CONTEXT.md`.
- Suggestion: cap file sizes / skip binaries; consider ignoring `.dbg/` and other generated dirs.

### `src/debugger/steps/repro_plan.py`
- Good: provides a deterministic template; always emits `REPRO.md`.
- Suggestion: optionally emit a `REPRO_CLASSIFICATION.json` to enable judging on repro rigor.

### `src/debugger/steps/track_iterate.py`
- Good: stores both `ITERATION.txt` and `ITERATION.json`, and validates schema via Pydantic.
- Suggestion: redact `ITERATION.json` too if it can contain secrets (currently only redacts text).

### `src/debugger/steps/verify.py`
- Good: contract-based verify execution with log capture.
- Fix applied: command `name` is sanitized for log filenames (prevents path injection).
- Suggestion: include command duration and stdout/stderr byte counts in `verify.commands.json`.

### `src/debugger/steps/judge.py`
- Good: deterministic selection logic; honors disqualification.
- Suggestion: incorporate `SCORES.json` and/or iteration confidence more meaningfully over time.

### `src/debugger/steps/apply.py`
- Good: applies the winning patch and records exit code to `APPLY.md`.
- Suggestion: support `git apply --check` first and record a clearer failure reason on mismatch.

## Templates

### `src/debugger/templates/__init__.py`
- Empty marker file; ok.

### `src/debugger/templates/issue.md`
- Good: minimal “issue-like prompt” structure; works for `--issue-file`.

### `src/debugger/templates/tracks.yaml`
- Good: sensible defaults; manual providers are safe by default.

### `src/debugger/templates/verify_contract.yaml`
- Good: includes pytest + ruff hooks.
- Note: `mypy` is listed but not installed by default (it’s optional and `required: false`).

## Utilities

### `src/debugger/util/__init__.py`
- Empty marker file; ok.

### `src/debugger/util/events.py`
- Good: JSONL event stream is cheap and useful for postmortems.
- Suggestion: include `run_id` in every event (or have `EventLog` configured with it).

### `src/debugger/util/ids.py`
- Good: generates timestamped run IDs.
- Fix applied: added validation helpers to prevent unsafe `run_id`/track names.

### `src/debugger/util/paths.py`
- Good: template copier uses packaged resources.
- Fix applied: added `safe_filename()` to safely derive log filenames from user-provided names.
- Suggestion: migrate from `importlib.resources.open_text` to `files()` API if you want to avoid
  deprecation warnings in newer Python versions.

### `src/debugger/util/redaction.py`
- Good: minimal redaction baseline.
- Fix applied: uses `field(default_factory=...)` instead of `None` + mutation in `__post_init__`.
- Suggestion: allow patterns to be loaded from config for per-org secret formats.

### `src/debugger/util/shell.py`
- Good: captures stdout/stderr to files; callers inspect return code.
- Suggestion: capture elapsed time and include it in `CmdResult` (helps judging and debugging).

### `src/debugger/util/text.py`
- Minimal helper; ok.

## Tests

### `tests/test_schemas.py`
- Good: covers basic schema validation for `IterationEnvelope` and `RunStatus`.
- Suggestion: add one test asserting packaged templates/profiles can be read via
  `importlib.resources` (guards packaging changes).
