from __future__ import annotations

"""Provider protocol definition.

CONTRACT
- Inputs: Repo, track, iteration, role, directions, context, blackboard
- Outputs (required):
  - ProviderResult (text, iteration_json, patch_diff, meta)
- Invariants:
  - iteration_json must roughly follow IterationEnvelope shape (checked by track_iterate)
  - Must not crash on normal provider errors (raise specific exceptions to be caught)
- Failure:
  - Raises RuntimeError/ValueError on provider execution failure
"""

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
