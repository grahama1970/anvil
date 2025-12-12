# Anvil Project Context

> Last Updated: 2025-12-12 | Tests: 44/44 passed

## What is Anvil?

Anvil is a **no-vibes debugging and hardening orchestrator** designed to be called by AI orchestrator agents. It runs parallel AI tracks to fix bugs or find vulnerabilities.

## Two Core Modes

1. **Debug Mode**: Fix a known bug. Takes issue description, spawns parallel AI tracks, picks winner.
2. **Harden Mode**: Proactively find vulnerabilities. Runs "breaker" tracks to discover bugs, missing tests.

## Simple API (for orchestrator agents)

```python
import anvil

# Debug a known bug
result = anvil.debug("/path/to/repo", "Login crashes on click")

# Harden a codebase
result = anvil.harden("/path/to/repo")
```

## CLI (for humans)

```bash
anvil debug run --repo . --issue "Bug description"
anvil harden run --repo .
```

## Current State

### What Works ✅

- **Debug mode**: Full implementation with parallel tracks, judging, auto-apply
- **Harden mode**: Full implementation with breaker tracks, HARDEN.md report
- **Prompt fix**: LLMs now generate actual patches (not NO_PATCH)
- **Auto-apply**: Controlled by `ANVIL_AUTO_APPLY` env var (default: enabled)
- **Schema validation**: `validate_iteration_json()` function added
- **Tests**: 44/44 passing (including harden-specific tests)
- **README**: Updated with Simple API examples

### Key Files

- `src/anvil/__init__.py` - Simple `debug()` and `harden()` API
- `src/anvil/orchestrator.py` - Core logic for both modes
- `src/anvil/providers/common.py` - Prompt that forces patch generation
- `src/anvil/artifacts/schemas.py` - Pydantic schemas + validation functions
- `docs/CONTRACT.md` - System contract (updated with harden artifacts)

### Providers

- `copilot`: GitHub Copilot CLI (uses gpt-5, claude-sonnet, etc.)
- `gemini`: Gemini CLI
- `manual`: Generates templates for human editing

## Recent Changes (This Session)

1. **Fixed import errors**: Changed all tests from `src.anvil` to `anvil` imports
2. **Added harden-specific tests**: Created `tests/test_harden.py` with 5 new tests
3. **Updated README**: Added Simple API section with Python examples
4. **Fixed harden mode bugs**:
   - Added `directions_text` parameter to `TrackIterate.run()` for custom directions
   - Fixed `Blackboard` method call (was calling non-existent method)
5. **Verified validation enforcement**: Already implemented in `TrackIterate.check()`
6. **Tested harden mode live**: Successfully ran against Anvil repo, generates HARDEN.md

## Artifacts Generated

### Debug Mode

- `CONTEXT.md` - Repo context for AI
- `FILES.json` - Index of files in context
- `REPRO.md` - Reproduction plan
- `tracks/<name>/iter_NN/ITERATION.json` - Structured AI response
- `tracks/<name>/iter_NN/PATCH.diff` - Generated patch
- `VERIFY.md` - Verification results
- `SCORECARD.json` - Track scores
- `DECISION.md` - Winner selection

### Harden Mode

- Same as above, plus:
- `HARDEN.md` - Report with findings and patches
- `BLACKBOARD.md` - Shared observations

## Next Steps

All items complete! ✅

1. ✅ ~~**Add harden-specific tests**: Create `tests/test_harden.py`~~ - Done
2. ✅ ~~**Document in README**: Update README with simple API examples~~ - Done
3. ✅ ~~**Test harden mode live**: Run `anvil harden run --repo .`~~ - Done, fixed 2 bugs
4. ✅ ~~**Add validation enforcement**~~ - Already implemented in `TrackIterate.check()`

## Commands to Verify

```bash
# Run all tests
uv run pytest tests/ -v

# Check CLI works
uv run python -m anvil.cli --help

# Run debug on itself
uv run python -m anvil.cli debug run --repo . --issue "Add missing test" --tracks-file dogfood/tracks.yaml

# Run harden on itself
uv run python -m anvil.cli harden run --repo .
```
