from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderResult:
    text: str
    iteration_json: dict[str, Any]
    patch_diff: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class Provider(Protocol):
    def run_iteration(
        self,
        *,
        repo: Path,
        track: str,
        iteration: int,
        role: str,
        directions: str,
        context: str,
        blackboard: str,
    ) -> ProviderResult: ...
