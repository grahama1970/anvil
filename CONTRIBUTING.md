# Contributing to Anvil

We welcome contributions! This guide will help you set up your development environment.

## Development Setup

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/google-deepmind/anvil.git
    cd anvil
    ```

2.  **Create a virtual environment:**

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -e ".[dev]"
    ```
    _Note: If `[dev]` extras are not defined yet, just use `pip install -e .` and manually install `pytest`._

## Running Tests

We use `pytest` for testing.

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_reachability.py

# Run with output capture disabled (for debugging)
pytest -s
```

## Project Structure

- `src/debugger/`: Main package source.
  - `cli.py`: Entry point (`anvil` command).
  - `orchestrator.py`: Main logic driving the debug loop.
  - `steps/`: Individual pipeline steps (Context, Repro, Iterate, etc.).
  - `providers/`: LLM integration implementations (Gemini, Copilot, Manual).
  - `artifacts/`: Schema definitions and storage logic.

## Adding a New Provider

1.  Create a new file in `src/debugger/providers/` (e.g., `my_llm.py`).
2.  Inherit from `Provider` base class (`src/debugger/providers/base.py`).
3.  Implement `run_iteration`.
4.  Register it in `src/debugger/config.py`.

## Code Style

- We use `black` and `isort` (or similar standard formatters).
- Type hints are required for all new code.
- All new features must include tests.

## Artifacts & Contracts

Anvil relies heavily on "Artifact Contracts" to ensure robust interaction between steps.
See the `CONTRACT` docstrings at the top of each module in `src/debugger/steps/` for input/output requirements.
