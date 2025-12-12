FROM python:3.11.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates ripgrep jq \
  && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir "uv==0.7.10"

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock README.md /app/

# Install dependencies (without project itself)
RUN uv venv && uv sync --frozen --no-dev --no-install-project

# Copy source code and docs
COPY src /app/src
COPY AGENTS.md /app/AGENTS.md

# Install the project
RUN uv sync --frozen --no-dev

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Declare volumes for artifacts and worktrees
VOLUME ["/repo/.dbg"]

# Health check - verify anvil is installed
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD anvil --help || exit 1

# Support both 'anvil' and legacy 'dbg' commands
ENTRYPOINT ["anvil"]
