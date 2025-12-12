"""Gemini CLI provider.

CONTRACT
- Invokes `gemini` in one-shot mode.
- Returns a valid IterationEnvelope-like JSON object (schema_version=1).
- May optionally return a unified diff.
- If `gemini` is not available or the output can't be parsed, raises an exception.

Notes
- Model selection is per-track (`tracks.yaml`: `provider: gemini`, `model: gemini-3-pro`, etc.).
- We request text output and parse strict BEGIN/END markers to keep results deterministic.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..util.shell import which
from .base import Provider, ProviderResult

_BEGIN_JSON = "BEGIN_ITERATION_JSON"
_END_JSON = "END_ITERATION_JSON"
_BEGIN_DIFF = "BEGIN_PATCH_DIFF"
_END_DIFF = "END_PATCH_DIFF"


def _between(text: str, start: str, end: str) -> str | None:
    if start not in text:
        return None
    after = text.split(start, 1)[1]
    if end not in after:
        return None
    return after.split(end, 1)[0].strip()


def _normalize_iteration_json(
    it: dict[str, Any], *, track: str, iteration: int, has_patch: bool
) -> dict[str, Any]:
    it.setdefault("schema_version", 1)
    it["track"] = track
    it["iteration"] = iteration
    it.setdefault("status_signal", "NEEDS_MORE_WORK")
    it.setdefault("hypothesis", "")
    it.setdefault("confidence", 0.0)
    it.setdefault("experiments", [])
    it.setdefault("proposed_changes", {})
    if isinstance(it["proposed_changes"], dict):
        it["proposed_changes"].setdefault("has_patch", has_patch)
    it.setdefault("risks", [])
    return it


def _build_prompt(
    *,
    track: str,
    iteration: int,
    role: str,
    directions: str,
    context: str,
    blackboard: str,
) -> str:
    schema_hint = {
        "schema_version": 1,
        "track": track,
        "iteration": iteration,
        "status_signal": "CONTINUE | SKIP_TO_VERIFY | READY_FOR_FIX | NEEDS_MORE_WORK",
        "hypothesis": "string",
        "confidence": 0.0,
        "experiments": [],
        "proposed_changes": {"has_patch": False},
        "risks": [],
    }
    return (
        "You are a contract-driven debugging agent.\n"
        "\n"
        f"ROLE: {role}\n"
        "\n"
        "DIRECTIONS:\n"
        f"{directions}\n"
        "\n"
        "BLACKBOARD (observations-only):\n"
        f"{blackboard}\n"
        "\n"
        "CONTEXT:\n"
        f"{context}\n"
        "\n"
        "Return ONLY the following markers and contents.\n"
        f"{_BEGIN_JSON}\n"
        "JSON must be a single object matching this shape:\n"
        f"{json.dumps(schema_hint, indent=2)}\n"
        f"{_END_JSON}\n"
        f"{_BEGIN_DIFF}\n"
        "Either a unified diff (git-style) OR the literal text NO_PATCH.\n"
        f"{_END_DIFF}\n"
    )


@dataclass
class GeminiCliProvider(Provider):
    gemini_cmd: str = "gemini"
    model: str = "gemini-3-pro"
    timeout_s: int = 600

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
        if which(self.gemini_cmd) is None:
            raise RuntimeError("gemini CLI not found in PATH")

        prompt = _build_prompt(
            track=track,
            iteration=iteration,
            role=role,
            directions=directions,
            context=context,
            blackboard=blackboard,
        )

        args = [
            self.gemini_cmd,
            "--model",
            self.model,
            "--output-format",
            "text",
            "--prompt",
            prompt,
        ]
        proc = subprocess.run(
            args,
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
        )
        combined = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        if proc.returncode != 0:
            raise RuntimeError(f"gemini failed (rc={proc.returncode}). Output:\n{combined}")

        json_block = _between(combined, _BEGIN_JSON, _END_JSON)
        if not json_block:
            raise ValueError("gemini output missing iteration JSON markers")
        it = json.loads(json_block)
        if not isinstance(it, dict):
            raise ValueError("iteration JSON must be an object")

        diff_block = _between(combined, _BEGIN_DIFF, _END_DIFF)
        patch_diff = None
        if diff_block and diff_block.strip() != "NO_PATCH":
            patch_diff = diff_block.strip() + "\n"

        it = _normalize_iteration_json(
            it, track=track, iteration=iteration, has_patch=bool(patch_diff)
        )
        return ProviderResult(
            text=combined,
            iteration_json=it,
            patch_diff=patch_diff,
            meta={"provider": "gemini", "model": self.model},
        )
