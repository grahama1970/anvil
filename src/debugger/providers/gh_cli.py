"""GitHub CLI provider (stub).

CONTRACT
- Inputs: Repo, track, iteration
- Outputs:
  - Raises RuntimeError (stub implementation)
- Invariants:
  - Checks for `gh` CLI presence before raising stub error
- Failure:
  - Always fails with RuntimeError (instruction to customize)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..util.shell import which
from .base import Provider, ProviderResult


@dataclass
class GhCliProvider(Provider):
    gh_cmd: str = "gh"

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
    ) -> ProviderResult:
        if which(self.gh_cmd) is None:
            raise RuntimeError("gh CLI not found in PATH")
        # Placeholder: write prompt to a file and use gh as a transport (user will customize).
        # We keep a basic command that will usually fail unless user wires it.
        # This is intentional: avoids pretending we can call models without config.
        raise RuntimeError(
            "GhCliProvider is a stub. Customize run_iteration() to call your GitHub agent/Copilot "
            "backend."
        )
