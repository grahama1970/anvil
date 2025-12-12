from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .base import Provider, ProviderResult


@dataclass
class ManualProvider(Provider):
    """Offline/manual provider.

    Produces a structured iteration template and no patch.
    """

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
        it = {
            "schema_version": 1,
            "track": track,
            "iteration": iteration,
            "status_signal": "CONTINUE",
            "hypothesis": f"(fill) Hypothesis for {role}",
            "confidence": 0.0,
            "experiments": [
                {
                    "name": "(fill) experiment name",
                    "command": "(fill) command you ran",
                    "expected": "(fill) expected",
                    "observed_artifact": "(fill) path to artifact log",
                }
            ],
            "proposed_changes": {"has_patch": False},
            "risks": [],
        }
        text = (
            f"MANUAL PROVIDER TEMPLATE\n"
            f"- role: {role}\n"
            f"- directions: {directions}\n"
            f"Fill ITERATION.json and optionally PATCH.diff, then rerun resume.\n"
        )
        return ProviderResult(
            text=text, iteration_json=it, patch_diff=None, meta={"provider": "manual"}
        )
