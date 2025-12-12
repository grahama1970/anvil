from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..artifacts.store import ArtifactStore


class Step(Protocol):
    name: str

    def run(self, store: ArtifactStore, repo: Path) -> None: ...
    def check(self, store: ArtifactStore, repo: Path) -> int: ...
