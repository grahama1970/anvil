FROM python:3.11.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates ripgrep jq \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "uv==0.7.10"

WORKDIR /app

COPY pyproject.toml uv.lock README.md /app/

RUN uv venv && uv sync --frozen --no-dev --no-install-project

COPY src /app/src
COPY AGENTS.md /app/AGENTS.md

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["dbg"]
