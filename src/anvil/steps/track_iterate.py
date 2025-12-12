"""Track iteration step.

CONTRACT
- Inputs: ArtifactStore, Repo path, track name, role, provider, iteration, directions profile, context, blackboard
- Outputs (required):
  - tracks/<track>/iter_<NN>/ITERATION.json
  - tracks/<track>/iter_<NN>/ITERATION.txt
- Outputs (optional):
  - tracks/<track>/iter_<NN>/PATCH.diff
- Invariants:
  - ITERATION.json follows IterationEnvelope schema (schema_version=1)
  - Retries on provider checks are NOT handled here (handled by Policy/Orchestrator)
- Failure:
  - check() returns 2 if ITERATION.json is missing or invalid
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from ..artifacts.schemas import IterationEnvelope
from ..artifacts.store import ArtifactStore
from ..contracts.validate import check_required_artifacts
from ..prompts.load import load_profile
from ..providers.base import Provider, ProviderResult
from ..util.redaction import Redactor


@dataclass
class TrackIterate:
    name: str = "track_iterate"
    redactor: Redactor = Redactor()

    async def run(
        self,
        *,
        store: ArtifactStore,
        repo: Path,
        track: str,
        role: str,
        provider: Provider,
        iteration: int,
        context_text: str,
        blackboard_text: str,
        directions_profile: str = "strict_minimal_patch",
        directions_text: str | None = None,
    ) -> None:
        # Use raw directions_text if provided, otherwise load from profile
        directions = directions_text if directions_text else load_profile(directions_profile)
        try:
            result = await provider.run_iteration(
                repo=repo,
                track=track,
                iteration=iteration,
                role=role,
                directions=directions,
                context=context_text,
                blackboard=blackboard_text,
            )
        except Exception as exc:
            it = {
                "schema_version": 1,
                "track": track,
                "iteration": iteration,
                "status_signal": "NEEDS_MORE_WORK",
                "hypothesis": "Provider invocation failed; see ITERATION.txt for details.",
                "confidence": 0.0,
                "experiments": [],
                "proposed_changes": {"has_patch": False, "provider_error": str(exc)},
                "risks": ["provider_error"],
            }
            result = ProviderResult(
                text=f"PROVIDER ERROR: {exc}\n",
                iteration_json=it,
                patch_diff=None,
                meta={"provider_error": str(exc)},
            )

        iter_dir = store.path("tracks", track, f"iter_{iteration:02d}")
        iter_dir.mkdir(parents=True, exist_ok=True)

        # Redact text outputs defensively.
        result_text = result.text or "(No text output from provider)"
        (iter_dir / "ITERATION.txt").write_text(self.redactor.redact(result_text), encoding="utf-8")

        # Task 4.6: Redact ITERATION.json content
        # We redact the JSON string to catch secrets in values 
        # (simpler than traversing dict)
        json_str = json.dumps(result.iteration_json, indent=2, ensure_ascii=False)
        (iter_dir / "ITERATION.json").write_text(self.redactor.redact(json_str) + "\n", encoding="utf-8")

        if result.patch_diff:
            (iter_dir / "PATCH.diff").write_text(result.patch_diff, encoding="utf-8")

    def check(self, store: ArtifactStore, repo: Path, track: str, iteration: int) -> int:
        iter_rel = f"tracks/{track}/iter_{iteration:02d}/ITERATION.json"
        res = check_required_artifacts(store.run_dir, [iter_rel])
        if res.exit_code != 0:
            store.write_json(
                f"tracks/{track}/iter_{iteration:02d}/CHECK_iterate.json", res.model_dump()
            )
            return res.exit_code

        # Validate schema.
        try:
            raw = json.loads((store.run_dir / iter_rel).read_text(encoding="utf-8"))
            IterationEnvelope.model_validate(raw)
            ok = True
            exit_code = 0
            details = "OK"
        except (json.JSONDecodeError, ValidationError) as e:
            ok = False
            exit_code = 2
            details = f"Invalid ITERATION.json schema: {e}"

        out = {
            "schema_version": 1,
            "name": "iterate_schema",
            "ok": ok,
            "exit_code": exit_code,
            "details": details,
            "required_artifacts": [iter_rel],
            "missing_artifacts": [],
        }
        store.write_json(f"tracks/{track}/iter_{iteration:02d}/CHECK_iterate.json", out)
        return exit_code

if __name__ == "__main__":
    import argparse
    import sys

    from ..providers.manual import ManualProvider

    parser = argparse.ArgumentParser(description="Track Iterate Step (Manual Provider)")
    parser.add_argument("--repo", required=True, help="Path to repo")
    parser.add_argument("--track", required=True, help="Track name")
    parser.add_argument("--role", default="debugger", help="Role name")
    parser.add_argument("--iteration", type=int, default=1, help="Iteration number")
    parser.add_argument("--profile", required=True, help="Directions profile name")
    parser.add_argument("--context", default="", help="Context text")
    parser.add_argument("--blackboard", default="", help="Blackboard text")
    parser.add_argument("--out-dir", required=True, help="Output directory for artifacts")
    args = parser.parse_args()

    import asyncio
    
    async def main():
        store = ArtifactStore(Path(args.out_dir))
        step = TrackIterate()
        await step.run(
            store=store,
            repo=Path(args.repo),
            track=args.track,
            role=args.role,
            provider=ManualProvider(),
            iteration=args.iteration,
            directions_profile=args.profile,
            context_text=args.context,
            blackboard_text=args.blackboard,
        )
        sys.exit(step.check(store, Path(args.repo), args.track, args.iteration))

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
