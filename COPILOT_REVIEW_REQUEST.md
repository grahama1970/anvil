# Comprehensive Code Review Request: Anvil Project

## Repository and Origin

- **Repo:** `grahama1970/anvil`
- **Branch:** `main`
- **Forked/Inspired by:** [`nicobailon/debug-mode`](https://github.com/nicobailon/debug-mode)
- **Key difference:** Anvil extends debug-mode with **harden mode** for proactive vulnerability finding, N-track configuration, and a Python API.

---

## Summary

Anvil is a **no-vibes debugging and hardening orchestrator** for AI agents. It spawns parallel AI tracks to fix bugs (debug mode) or find vulnerabilities (harden mode), using artifact-backed scoring to select winners.

**Request:** Comprehensive code review focusing on:

1. Code correctness and architecture
2. Documentation quality and alignment
3. Developer experience (QUICKSTART, README)
4. Feature completeness vs. original debug-mode

---

## Part 1: Core Architecture Review

### 1.1 Orchestrator (`src/anvil/orchestrator.py`)

**Review focus:**

- Is `run_debug_session()` logic correct for parallel track execution?
- Is `run_harden_session()` properly isolated from debug mode?
- Are crash isolation patterns consistent between modes?
- Is resume logic correct (checks CHECK_iterate.json)?

**Key functions:** `run_debug_session`, `run_harden_session`, `_process_track`, `_process_breaker_track`

```
Lines of interest: ~650 lines
```

### 1.2 Steps Package (`src/anvil/steps/`)

**Files to review:**

- `track_iterate.py` - Provider iteration + validation
- `judge.py` - Winner selection with scoring
- `repro_assess.py` - Reproduction mode detection (NEW)
- `verify.py` - Test/lint verification
- `context_builder.py` - Codebase context generation

**Questions:**

1. Is the validation chain in `TrackIterate.check()` sufficient?
2. Is Judge scoring role-aware (fixer vs breaker)?
3. Does ReproAssess correctly detect pytest/npm/Makefile?

### 1.3 Providers (`src/anvil/providers/`)

**Files to review:**

- `copilot_cli.py` - GitHub Copilot integration
- `gemini_cli.py` - Gemini CLI integration
- `claude_cli.py` - Claude CLI integration
- `common.py` - Prompt building + JSON normalization

**Questions:**

1. Are all providers implementing the `Provider` protocol correctly?
2. Is `build_prompt()` role-aware (fixer requires patches, breaker optional)?
3. Is `normalize_iteration_json()` robust against malformed LLM output?

### 1.4 Worktree Management (`src/anvil/worktrees.py`)

**Review focus:**

- Is `create_worktrees()` idempotent?
- Does `cleanup()` correctly archive branches?
- Is `_archive_branch()` naming convention correct (`archive/anvil-{run_id}-{track}-{timestamp}`)?

---

## Part 2: Documentation Alignment Review

### 2.1 README.md

**Review criteria (Problem/Solution focused):**

- [ ] Does it clearly state the PROBLEM Anvil solves?
- [ ] Does it explain the SOLUTION concisely?
- [ ] Is the value proposition scannable in <30 seconds?
- [ ] Are installation instructions accurate?
- [ ] Is the Simple API section accurate?

**Specific checks:**

1. Do the Python API examples (`anvil.debug()`, `anvil.harden()`) work as shown?
2. Are CLI commands accurate and tested?
3. Does the feature list match what's implemented?

### 2.2 QUICKSTART.md (if exists, or should we create one?)

**Review criteria (Developer Experience):**

- [ ] Can a developer go from zero to working in <5 minutes?
- [ ] Are prerequisites clearly listed?
- [ ] Is there a working copy-paste example?
- [ ] Are common errors and solutions documented?

**Expected flow:**

```bash
# Install
uv pip install anvil  # or pip install .

# Quick test
anvil debug run --repo . --issue "Test" --artifacts-dir /tmp/test

# See results
cat /tmp/test/*/HARDEN.md
```

### 2.3 docs/CONTRACT.md

**Review criteria:**

- [ ] Are all step contracts documented?
- [ ] Do actual implementations match documented contracts?
- [ ] Are artifact schemas documented?

### 2.4 CONTEXT.md

**Review criteria:**

- [ ] Is it up-to-date with current state?
- [ ] Does it accurately describe test count?
- [ ] Are recent changes documented?

---

## Part 3: Feature Completeness vs debug-mode

### Feature Comparison Table

| Feature             | debug-mode | Anvil | Notes                                |
| ------------------- | ---------- | ----- | ------------------------------------ |
| Dual-track parallel | ✅         | ✅    | Verify equivalent                    |
| Git worktrees       | ✅         | ✅    | Verify equivalent                    |
| Repro modes         | ✅         | ✅    | NEW: ReproAssess step                |
| Branch archiving    | ✅         | ✅    | NEW: cleanup(archive=True)           |
| Signals             | ✅         | ✅    | CONTINUE, SKIP_TO_VERIFY, etc.       |
| Judging             | ✅         | ✅    | Score-based                          |
| Auto-apply          | ✅         | ✅    | ANVIL_AUTO_APPLY env var             |
| tmux integration    | ✅         | ❌    | Different approach (subprocess)      |
| **Harden mode**     | ❌         | ✅    | EXTRA: Breaker tracks                |
| **N-track config**  | ❌         | ✅    | EXTRA: tracks.yaml                   |
| **Resume support**  | ❌         | ✅    | EXTRA: --resume flag                 |
| **Python API**      | ❌         | ✅    | EXTRA: anvil.debug(), anvil.harden() |

**Questions:**

1. Are there any debug-mode features we're missing?
2. Is our implementation of repro modes equivalent?
3. Should we add tmux integration for parity?

---

## Part 4: Test Coverage Review

**Current state:** 51 tests passing

### Test Files

| File                    | Count | Coverage             |
| ----------------------- | ----- | -------------------- |
| `test_harden.py`        | 5     | Harden mode          |
| `test_repro_assess.py`  | 7     | Repro detection      |
| `test_cli.py`           | 6     | CLI commands         |
| `test_judge_scoring.py` | 2     | Judge logic          |
| `test_providers.py`     | 3     | Provider abstraction |
| (others)                | 28    | Various              |

**Questions:**

1. Are critical paths adequately covered?
2. Are edge cases tested (empty repos, no git, etc.)?
3. Should we add integration tests that run actual LLM providers?

---

## Part 5: Specific Code Review Requests

### 5.1 Role-Aware Scoring (judge.py)

```python
# Lines 83-100: Is this logic correct?
if "breaker" in t.lower() or "explorer" in t.lower():
    track_role = "breaker"
# ...
if track_role == "fixer":
    score -= 50.0  # No patch penalty
else:
    score -= 10.0  # Reduced penalty for breaker
```

**Question:** Should role detection be based on TrackConfig.role instead of track name?

### 5.2 Resume Validation (orchestrator.py)

```python
# Lines 238-268: Resume checks CHECK_iterate.json
if check_path.exists():
    check_data = json.loads(check_path.read_text())
    if check_data.get("exit_code", 2) != 0:
        break  # Don't count failed iterations
```

**Question:** Is this the right granularity for resume?

### 5.3 Harden Directions (orchestrator.py)

```python
# Lines 482-490: Hardcoded harden directions
harden_directions = (
    "You are a security/quality breaker agent.\n"
    "Your goal: Find bugs, vulnerabilities..."
)
```

**Question:** Should harden directions be configurable via profile files like debug mode?

### 5.4 Blackboard Writes (orchestrator.py)

```python
# Line 525: Writes ALL tracks after each iteration
Blackboard().write(store, [tr.name for tr in tracks])
```

**Question:** Is this causing excessive file I/O? Should we throttle or lock?

---

## Clarifying Questions

1. **QUICKSTART.md:** Does one exist? If not, should we create it?

2. **API stability:** Are the `anvil.debug()` and `anvil.harden()` function signatures final?

3. **Provider priority:** Should copilot be the default? What if not installed?

4. **Docker mode:** Is `--docker` fully implemented and documented?

5. **Original debug-mode:** Are we properly attributing the inspiration? Should we add to README?

---

## Deliverables

Please provide:

1. **Architecture assessment:**

   - Correctness of parallel execution
   - Crash isolation patterns
   - Resume logic validity

2. **Documentation review:**

   - README.md: Problem/Solution clarity
   - QUICKSTART.md: Developer experience
   - Alignment between docs and code

3. **Code quality findings:**

   - Critical issues (must fix)
   - High priority issues (should fix)
   - Medium priority issues (nice to have)

4. **Feature gap analysis:**

   - Missing features from debug-mode
   - Suggested improvements

5. **Answers to clarifying questions**

---

## Verification Commands

```bash
# Run all tests
uv run pytest tests/ -v

# Test debug mode
uv run python -m anvil.cli debug run --repo . --issue "Test" --artifacts-dir /tmp/anvil-debug

# Test harden mode
uv run python -m anvil.cli harden run --repo . --artifacts-dir /tmp/anvil-harden

# Check Python API
python -c "import anvil; print(anvil.debug.__doc__)"

# List archived branches
git branch --list 'archive/anvil-*'
```

---

## Context for Reviewer

This project started as a Python reimplementation of [`nicobailon/debug-mode`](https://github.com/nicobailon/debug-mode), which is a TypeScript/Bun-based "Claude Code skill" for hypothesis-driven debugging.

Key differences in Anvil:

- Pure Python implementation
- Added **harden mode** for proactive security analysis
- Configurable N-track execution via YAML
- Python API in addition to CLI
- No tmux dependency (uses subprocess)
- Pydantic-based schema validation

The goal is to be a **standalone tool** that works with any LLM provider (copilot, gemini, claude) while maintaining the "no vibes" philosophy of artifact-backed decision making.
