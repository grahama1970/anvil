# Anvil Quickstart Guide

This guide will help you get up and running with Anvil in under 5 minutes.

## Prerequisites

- **Python 3.10+**
- **Git**
- (Optional) **Docker**: For running agents in isolated containers (recommended).

## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/grahama1970/anvil.git
    cd anvil
    ```

2.  **Install the package (editable mode recommended):**
    ```bash
    pip install -e .
    ```

## Usage

### 1. Initialize Anvil in a Target Repository

Navigate to the repository you want to debug (or use a fresh test repo).

```bash
# Example: Create a dummy repo
mkdir my-broken-repo
cd my-broken-repo
git init
echo "print('bug')" > main.py
git add . && git commit -m "Initial commit"

# Initialize Anvil
anvil init
```

This creates a `.dbg/` directory with configuration templates.

### 2. Configure Tracks

Edit `.dbg/tracks.yaml` to define your debugging sessions ("tracks").

```yaml
tracks:
  - name: feature_fix
    role: debugger
    provider: manual # Change to 'gemini' or 'copilot' if configured
    budgets:
      max_iters: 5
```

### 3. Run a Debug Session

Run the debugger with an issue description.

```bash
anvil debug run --issue "The main.py script prints 'bug' but should print 'hello'"
```

Anvil will:

1.  Scan your repository to build context (`CONTEXT.md`).
2.  Create a dedicated git worktree for the track.
3.  Start the agent loop (Manual, Gemini, etc.).

### 4. Inspect Artifacts

Artifacts are stored in `.dbg/runs/<run_id>/`.

```bash
ls -F .dbg/runs/latest/
# CONTEXT.md  FILES.json  RUN_STATUS.json  tracks/
```

Check the track output:

```bash
cat .dbg/runs/latest/tracks/feature_fix/iter_01/ITERATION.txt
```

## Docker Mode (Recommended for Isolation)

For security and reproducibility, run verify commands in Docker containers:

### Build the Image

```bash
docker build -t anvil:latest .
```

### Run with Docker Isolation

```bash
anvil debug run --issue "Bug description" --docker
```

The `--docker` flag runs all verify commands inside containers, isolating untrusted code execution.

### Docker Compose (Alternative)

```bash
# Initialize
docker-compose run --rm anvil init

# Debug with mounted repo
docker-compose run --rm anvil debug run --issue "Bug description"
```

Edit `docker-compose.yml` to mount your target repository.

## Next Steps

- Read [CONTRIBUTING.md](CONTRIBUTING.md) to learn how to add new providers.
- Check `src/anvil/config.py` for advanced configuration options.
