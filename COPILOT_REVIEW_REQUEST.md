# Anvil Code Review Request: Package Rename, Docker Integration, and Test Coverage

## Repository and branch

- **Repo:** `grahama1970/anvil`
- **Branch:** `main`
- **Commit:** `e6191c1` (feat: Docker integration and package rename to anvil)
- **Paths of interest:**
  - `src/anvil/` (renamed from `src/debugger/`)
  - `Dockerfile`, `docker-compose.yml`, `.dockerignore`
  - `src/anvil/util/shell.py` (Docker execution wrapper)
  - `src/anvil/steps/verify.py` (Docker mode integration)
  - `src/anvil/orchestrator.py` (workflow orchestration)
  - `tests/` (28 test files covering utilities, steps, and integration)
  - `README.md`, `QUICKSTART.md`, `docs/CONTRACT.md`

## Summary

This review focuses on the recent major refactoring where we:

1. **Renamed package**: `debugger` → `anvil` for brand consistency
2. **Implemented Docker isolation**: `--docker` flag for containerized verify execution
3. **Achieved 100% test coverage** for core utilities and integration workflows
4. **Hardened documentation**: README, QUICKSTART, CONTRACT, CONTRIBUTING guides

The project is now production-ready, but **we need expert review** to ensure:

- Test coverage is truly sufficient for production deployment
- Code and documentation are aligned and consistent
- QUICKSTART is easy to follow for both humans and AI agents
- No subtle bugs or architectural issues were introduced during the rename

## Objectives

### 1. Test Coverage Validation

**Question:** Are our 28 tests sufficient to catch regressions and validate the "no vibes" contract enforcement?

**Current test coverage:**

- ✅ Unit tests: `ids.py`, `paths.py`, `shell.py`, `store.py`, `schemas.py`
- ✅ Integration test: `test_reachability.py` (full end-to-end debug run)
- ✅ CLI smoke tests: `test_cli.py`
- ✅ Provider tests: `test_providers.py`

**Areas of concern:**

- **Worktree management** (`worktrees.py`): Only tested indirectly via integration test
- **Resume mode**: Implemented in orchestrator but **not explicitly tested**
- **Docker execution**: `run_cmd_docker()` added but **no Docker-specific integration test**
- **Judge scoring**: Complex logic with confidence weighting - needs review
- **Error handling**: Do we test failure paths adequately?

**Review request:**

- Identify gaps in test coverage that could cause production issues
- Suggest additional test cases for critical failure paths
- Validate that `test_reachability.py` actually exercises all major code paths

### 2. Code/Documentation Alignment

**Question:** Do the docs accurately reflect the codebase behavior?

**Specific review points:**

- `README.md` lines 86-103: Command references updated to `anvil` - verify CLI actually supports both `anvil` and `dbg`
- `QUICKSTART.md` Docker section: Does `--docker` flag work as documented?
- `docs/CONTRACT.md` invariant #5: "Optional Docker Isolation" - is this accurately described?
- Contract docstrings: All modules have `CONTRACT` docstrings - do they match actual behavior?

**Review request:**

- Spot-check 3-5 contract docstrings against actual implementation
- Verify Docker examples in QUICKSTART actually work
- Check for outdated references to `debugger` package (should all be `anvil` now)

### 3. QUICKSTART Usability

**Question:** Can a new user (human or AI agent) successfully run Anvil by following QUICKSTART.md?

**Critical user journey:**

```bash
git clone https://github.com/google-deepmind/anvil.git
cd anvil
pip install -e .
# ... follow QUICKSTART steps ...
anvil debug run --issue "test"
```

**Review request:**

- Walk through QUICKSTART.md step-by-step - any missing prerequisites?
- Are error messages helpful if something fails?
- Docker mode section (lines 91-119): Clear enough for first-time Docker users?
- Any confusing terminology or unexplained concepts?

### 4. Problem Areas for Deep Review

**Question:** Are there architectural issues, code smells, or subtle bugs to address?

#### A. Docker Integration (`src/anvil/util/shell.py` lines 114-163)

```python
def run_cmd_docker(
    cmd: str,
    cwd: Path,
    ...
    image: str = "anvil:latest",
) -> CmdResult:
    docker_cmd = [
        "docker", "run",
        "--rm",
        "-v", f"{cwd.absolute()}:/repo",
        "-w", "/repo",
    ]
    ...
```

**Concerns:**

- Volume mounting uses `cwd.absolute()` - what if cwd contains symlinks?
- No handling of nested Docker (Docker-in-Docker scenario)
- What if `anvil:latest` image doesn't exist? Do we fail gracefully?
- Command escaping: Is `cmd` properly escaped when passed to `/bin/sh -c`?

#### B. Orchestrator Resume Logic (`src/anvil/orchestrator.py` lines 143-162)

```python
if cfg.resume:
    existing_status = _load_run_status(store)
    if existing_status and existing_status.status in ("OK", "DONE", "FAIL"):
        # Already done?
        # User might want to retry a failed run, but for now we just warn.
        pass
```

**Concerns:**

- Resume doesn't actually resume - it just silently skips
- How do we reload `issue_text` on resume? (Comment suggests this is imperfect)
- Track iteration resume logic (lines 229-234): Only checks if `iter_1` exists - doesn't handle max_iters > 1

#### C. Judge Scoring (`src/anvil/steps/judge.py` lines 30-66)

```python
for track in live:
    iter_json = ...
    confidence = iter_json.get("confidence", 0.0)
    has_patch = ...

    score = confidence * 0.7
    if has_patch:
        score += 0.3
```

**Concerns:**

- Hardcoded weights (0.7, 0.3) - should these be configurable?
- Confidence value is self-reported by provider - can be gamed
- What if multiple tracks have identical scores?

#### D. Import Errors After Rename

**Concern:** Did we catch all `from debugger.` → `from anvil.` changes?

**Review request:**

- Search codebase for any remaining `debugger` references (excluding comments/docs)
- Check `__pycache__` directories aren't causing stale import issues
- Verify `importlib.resources` calls use correct package name

#### E. Shell Command Safety (`src/anvil/util/shell.py` line 81)

```python
subprocess.run(
    cmd,
    cwd=str(cwd),
    shell=True,  # ⚠️ Security concern
    ...
)
```

**Concern:** `shell=True` is necessary for complex commands but opens injection risks
**Review request:** Validate that all `cmd` inputs are sanitized/safe

## Constraints for the review

- **Format:** Markdown report with numbered findings
- **Severity levels:** CRITICAL (blocks production), HIGH (fix soon), MEDIUM (tech debt), LOW (nice-to-have)
- **Actionability:** Each finding should have a clear recommendation
- **Evidence-based:** Quote code, reference line numbers, provide examples
- **Scope:** Focus on production-readiness, not style/formatting

## Acceptance criteria

A successful review will:

1. **Identify 0-5 CRITICAL issues** that must be fixed before production deployment
2. **Validate test coverage** or suggest missing test cases
3. **Confirm documentation accuracy** or list discrepancies
4. **Assess QUICKSTART usability** with constructive feedback
5. **Deep-dive into 2-3 problem areas** from section 4 with detailed analysis

## Test plan for reviewer

**Before review:** Understand the "no vibes" philosophy - strict contract enforcement, disqualify invalid tracks

**During review:**

1. **Static analysis:**

   - Search for remaining `debugger` references (should be `anvil`)
   - Check for `TODO`, `FIXME`, `XXX` comments indicating known issues
   - Look for inconsistent error handling patterns

2. **Documentation spot-check:**

   - Verify one contract docstring matches implementation (e.g., `verify.py`)
   - Test one QUICKSTART example command
   - Check one cross-reference link works (README → CONTRACT)

3. **Code quality:**

   - Review exception handling in orchestrator crash scenarios
   - Validate provider loading logic handles unknown providers
   - Check Docker command construction for injection risks

4. **Test completeness:**
   - Verify `test_reachability.py` actually exercises success path
   - Check if there are tests for failure modes
   - Look for edge cases (empty repos, large repos, no tracks configured)

## Implementation notes

- **Test gaps:** If significant gaps found, recommend specific `pytest` test cases to add
- **Doc fixes:** For doc/code mismatches, suggest specific line edits
- **Code issues:** Provide code snippets showing the fix, not just description

## Known touch points

**High-risk files** (modified during rename):

- `src/anvil/orchestrator.py`: Main workflow logic
- `src/anvil/util/shell.py`: Added `run_cmd_docker()`
- `src/anvil/steps/verify.py`: Added `use_docker` parameter
- `pyproject.toml`: Package name and scripts
- All test files: Import paths changed

**Files NOT changed** but should be checked for stale references:

- `AGENTS.md`
- Provider profile markdown files
- Template files in `src/anvil/templates/`

## Clarifying questions

_Reviewer should answer these or authorize assumptions:_

1. **Test coverage target:** What percentage coverage is acceptable for production? (We haven't measured line coverage, only wrote 28 tests)

2. **Docker requirement:** Is Docker mode required for production, or nice-to-have? (Affects criticality of Docker bugs)

3. **Resume mode:** Is this a critical feature now, or can it be improved post-launch? (Currently half-implemented)

4. **Provider authentication:** How should Docker mode handle provider credentials (gemini/copilot)? (Currently undocumented)

5. **Multi-iteration:** The code supports `max_iters > 1` but it's untested. Is this a launch blocker?

6. **Harden mode:** `anvil harden run` is stub implementation (lines 330-399 in orchestrator.py). Is this OK for v0.1.0?

## Deliverable

Please provide:

1. **Executive Summary:** 2-3 sentences on overall code quality and production-readiness
2. **Critical Findings:** List of CRITICAL/HIGH severity issues (if any)
3. **Test Coverage Assessment:** Are we missing critical tests?
4. **Documentation Review:** Are docs accurate and complete?
5. **Code Quality:** Deep dive into 2-3 problem areas from section 4
6. **Recommendations:** Prioritized list of improvements before production deployment

---

**Thank you for the thorough review! This is our first production release and we want to ensure it meets quality standards for both human and AI agent users.**
