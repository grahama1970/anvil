from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .base import Provider, ProviderResult


@dataclass
class ManualProvider(Provider):
    """Manual provider.

    CONTRACT
    - Inputs: Repo, track, iteration, role, directions
    - Outputs:
      - ProviderResult with "NEEDS_MORE_WORK" signal and template text
    - Invariants:
      - Never produces a patch automatically (has_patch=False)
      - Intended for human-in-the-loop iteration
    - Failure:
      - None expected (offline)
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


if __name__ == "__main__":
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Manual Provider CLI")
    parser.add_argument("--repo", required=True, help="Path to repo")
    parser.add_argument("--track", required=True, help="Track name")
    parser.add_argument("--iteration", type=int, default=1, help="Iteration")
    parser.add_argument("--role", default="debugger", help="Role")
    parser.add_argument("--directions", default="", help="Directions text")
    args = parser.parse_args()

    try:
        provider = ManualProvider()
        res = provider.run_iteration(
            repo=Path(args.repo),
            track=args.track,
            iteration=args.iteration,
            role=args.role,
            directions=args.directions,
            context="",
            blackboard=""
        )
        print(json.dumps({
            "text": res.text,
            "iteration_json": res.iteration_json,
            "patch_diff": res.patch_diff,
            "meta": res.meta
        }, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
