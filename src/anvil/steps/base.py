from __future__ import annotations

"""Step protocol definition.

CONTRACT
- Inputs: ArtifactStore, Repo path
- Outputs:
  - run(): Modifies artifacts store (writes logs, results, etc.)
  - check(): Returns exit code (0=success, non-zero=failure)
- Invariants:
  - All steps must implement `run` and `check`
- Failure:
  - `check` returns non-zero exit code on failure
"""

from pathlib import Path
from typing import Protocol

from ..artifacts.store import ArtifactStore


class Step(Protocol):
    name: str

    def run(self, store: ArtifactStore, repo: Path) -> None: ...
    def check(self, store: ArtifactStore, repo: Path) -> int: ...
