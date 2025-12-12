# Code Review Request — `grahama1970/anvil` (debugger harness)

This request is for a full-project review focused on:

1. **Docs vs. code alignment** (README + templates vs. real behavior)
2. **CLI reachability** (every major “script/module” is runnable via a CLI path to reproduce/debug)
3. **Operational readiness** (uv + Docker reproducibility, basic hardening)

## Quick links (files to start with)

- Docs:
  - `README.md`
  - `AGENTS.md`
  - `REVIEW.md` (internal critique / notes)
- Packaging / deploy:
  - `pyproject.toml`
  - `uv.lock`
  - `Dockerfile`
  - `.dockerignore`
- CLI + orchestration:
  - `src/anvil/cli.py`
  - `src/anvil/orchestrator.py`
  - `src/anvil/config.py`
- Workflow steps:
  - `src/anvil/steps/context_builder.py`
  - `src/anvil/steps/repro_plan.py`
  - `src/anvil/steps/track_iterate.py`
  - `src/anvil/steps/verify.py`
  - `src/anvil/steps/judge.py`
  - `src/anvil/steps/apply.py`
- Providers (multi-model support):
  - `src/anvil/providers/manual.py`
  - `src/anvil/providers/copilot_cli.py`
  - `src/anvil/providers/gemini_cli.py`
  - `src/anvil/providers/gh_cli.py`
  - `src/anvil/providers/base.py`
- Templates (what `dbg init` writes):
  - `src/anvil/templates/tracks.yaml`
  - `src/anvil/templates/verify_contract.yaml`
  - `src/anvil/templates/issue.md`

## Reviewer goal #1 — Docs vs code mapping

Please verify that every claim in `README.md` has a concrete implementation and that any missing
features are clearly labeled as “stub/optional”.

### README: Command coverage

- `dbg init`
  - Docs: `README.md`
  - CLI: `src/anvil/cli.py` (`init`)
  - Impl: `src/anvil/init.py` (`write_templates`)
  - Templates: `src/anvil/templates/*`
- `dbg doctor`
  - Docs: `README.md`
  - CLI: `src/anvil/cli.py` (`doctor`)
  - Impl: `src/anvil/doctor.py` (`doctor_report`)
- `dbg debug run`
  - Docs: `README.md`
  - CLI: `src/anvil/cli.py` (`debug_run`)
  - Orchestrator: `src/anvil/orchestrator.py` (`run_debug_session`)
  - Step modules: `src/anvil/steps/*.py`
- `dbg debug status`, `dbg debug resume`
  - CLI: `src/anvil/cli.py` (`debug_status`, `debug_resume`)
- `dbg harden run`, `dbg harden status`
  - CLI: `src/anvil/cli.py`
  - Orchestrator: `src/anvil/orchestrator.py` (`run_harden_session`)

### README: Providers / multi-model claims

The repo is intended to support mixing providers/models per track (crucial requirement).

- Provider selection wiring (review carefully):
  - `src/anvil/orchestrator.py` (`_provider_for_track`)
  - `src/anvil/config.py` (`TrackConfig.provider`, `TrackConfig.model`, `TrackConfig.provider_options`)
- Providers:
  - `manual`: `src/anvil/providers/manual.py`
  - `copilot`: `src/anvil/providers/copilot_cli.py` (runs `copilot --model ... -p ...`)
  - `gemini`: `src/anvil/providers/gemini_cli.py` (runs `gemini --model ... --prompt ...`)
  - `gh_cli`: `src/anvil/providers/gh_cli.py` (explicit stub)

Please confirm the docs match actual supported values (`provider: manual|copilot|gemini|gh_cli`)
and that unsupported providers fail clearly in artifacts (not silent fallback).

### README: Tree-sitter utilities

- Docs: `README.md`
- Implementation/fallback behavior:
  - `src/anvil/treesitter_utils.py` (prefers local `treesitter-tools` if installed; otherwise falls back)
  - `pyproject.toml` (`dependency-groups.ast` using `file:///home/graham/workspace/experiments/treesitter-tools`)

## Reviewer goal #2 — “Every script has a runnable CLI path”

This project does not expose “one CLI per module file”. Instead, the design intent is:

- **One stable CLI** (`dbg`) that exercises the workflow end-to-end.
- Each major module is reachable through **at least one `dbg …` command** and produces artifacts/logs
  that can be inspected to debug failures.

Please verify the following “reachability matrix”:

### Primary CLI entrypoint

- Entry point: `pyproject.toml` → `[project.scripts] dbg = "anvil.cli:app"`
- Implementation: `src/debugger/cli.py`

### Workflow steps are runnable via `dbg debug run`

When you run `dbg debug run`, the orchestrator should execute these steps and create artifacts:

- Context: `src/debugger/steps/context_builder.py`
  - Expected artifacts: `.dbg/runs/<run_id>/CONTEXT.md`, `.dbg/runs/<run_id>/FILES.json`
- Repro plan: `src/debugger/steps/repro_plan.py`
  - Expected artifact: `.dbg/runs/<run_id>/REPRO.md`
- Track iteration: `src/debugger/steps/track_iterate.py`
  - Expected artifacts per track: `.dbg/runs/<run_id>/tracks/<track>/iter_01/ITERATION.json|txt`
- Verify: `src/debugger/steps/verify.py`
  - Expected artifacts: `.dbg/runs/<run_id>/VERIFY.md` + `.dbg/runs/<run_id>/logs/verify.*.log`
- Judge: `src/debugger/steps/judge.py`
  - Expected artifacts: `.dbg/runs/<run_id>/DECISION.md`, `.dbg/runs/<run_id>/SCORECARD.json`
- Apply: `src/debugger/steps/apply.py`
  - Expected artifact: `.dbg/runs/<run_id>/APPLY.md` (only when a patch exists)

### Providers are runnable via tracks config

Providers are exercised by `dbg debug run` depending on your `.dbg/tracks.yaml`.

Please validate that:

- A track can select `provider: copilot` and a Copilot model like `claude-sonnet-4.5` or `gpt-5`.
- A track can select `provider: gemini` and a Gemini model like `gemini-3-pro`.
- Provider failures end up in track artifacts (not a crash without logs).

Relevant code:

- `src/debugger/providers/copilot_cli.py`
- `src/debugger/providers/gemini_cli.py`
- `src/debugger/orchestrator.py`
- `src/debugger/steps/track_iterate.py`

## Reviewer goal #3 — Build/deploy reproducibility + basic hardening

### Reproducible env (uv)

- Root venv convention: `.python-version` + `uv venv --python=3.11.12 .venv`
- Lockfile: `uv.lock`
- Packaging config: `pyproject.toml`

Suggested checks:

```bash
uv venv --python=3.11.12 .venv
uv sync
uv run ruff check .
uv run pytest
uv build
```

### Reproducible Docker image

- Docker build logic: `Dockerfile`
  - Uses `python:3.11.12-slim`
  - Pins `uv==0.7.10`
  - Uses `uv.lock` + `--frozen --no-dev`
- Ignore list: `.dockerignore`

Suggested checks:

```bash
docker build -t debugger:local .
docker run --rm debugger:local --help
```

### Security / robustness checks (please focus here)

I would like reviewers to look closely at:

- Path safety for artifacts/log output:
  - `src/debugger/artifacts/store.py` (prevents writing outside `.dbg/runs/<id>/`)
  - `src/debugger/steps/verify.py` (sanitizes verify command names used in filenames)
- Input validation:
  - `src/debugger/util/ids.py` (`validate_run_id`, `validate_track_name`)
  - `src/debugger/cli.py` (validates run ids and candidate refs)
  - `src/debugger/config.py` (validates track names loaded from YAML)
- Subprocess invocation (shell vs argv):
  - Providers: `src/debugger/providers/copilot_cli.py`, `src/debugger/providers/gemini_cli.py`
  - Generic runner: `src/debugger/util/shell.py`

## What I want feedback on (explicit questions)

1. **Docs accuracy:** Is anything in `README.md` misleading vs what the code actually does today?
2. **Provider selection:** Is the provider/model configuration ergonomic enough for humans and the orchestrator?
3. **CLI coverage:** Do you agree that “one CLI with reachability matrix” satisfies “every script is runnable”,
   or do you want additional debug subcommands (e.g., `dbg step verify`, `dbg provider test`)?
4. **Docker expectation:** Should the Docker image include Copilot/Gemini CLIs, or should those remain host-only?
5. **Hardening:** Any remaining obvious injection/escape surfaces or unsafe defaults?
