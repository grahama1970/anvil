"""Track iteration step.

CONTRACT
- Per track, per iteration outputs (required):
  - tracks/<track>/iter_<NN>/ITERATION.json
  - tracks/<track>/iter_<NN>/ITERATION.txt
- Optional:
  - tracks/<track>/iter_<NN>/PATCH.diff
- Invariants:
  - ITERATION.json schema_version=1 and required fields exist
- Disqualification:
  - missing ITERATION.json or invalid schema => exit 2 on check
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

    def run(
        self,
        *,
        store: ArtifactStore,
        repo: Path,
        track: str,
        role: str,
        provider: Provider,
        iteration: int,
        directions_profile: str,
        context_text: str,
        blackboard_text: str,
    ) -> None:
        directions = load_profile(directions_profile)
        try:
            result = provider.run_iteration(
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
        (iter_dir / "ITERATION.txt").write_text(self.redactor.redact(result.text), encoding="utf-8")

        (iter_dir / "ITERATION.json").write_text(
            json.dumps(result.iteration_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

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
