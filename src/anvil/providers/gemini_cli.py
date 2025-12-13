"""Gemini CLI provider.

CONTRACT
- Inputs: Repo, track, iteration, role, directions, context
- Outputs (required):
  - ProviderResult with parsed JSON and optional patch
- Invariants:
  - Invokes `gemini` CLI with specified model
  - Enforces strict BEGIN_ITERATION_JSON markers
- Failure:
  - Raises RuntimeError if gemini CLI fails or returns non-zero
  - Raises ValueError if output format is invalid
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..util.shell import which
from .base import Provider, ProviderResult
from .common import extract_between, normalize_iteration_json, build_prompt

_BEGIN_JSON = "BEGIN_ITERATION_JSON"
_END_JSON = "END_ITERATION_JSON"
_BEGIN_DIFF = "BEGIN_PATCH_DIFF"
_END_DIFF = "END_PATCH_DIFF"


@dataclass
class GeminiCliProvider(Provider):
    gemini_cmd: str = "gemini"
    model: str = "gemini-3-pro"
    timeout_s: int = 600

    async def run_iteration(
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

        prompt = build_prompt(
            track=track,
            iteration=iteration,
            role=role,
            directions=directions,
            context=context,
            blackboard=blackboard,
        )

        args = [
            "--model",
            self.model,
            "--output-format",
            "text",
            "--prompt",
            prompt,
        ]
        
        import asyncio
        import os

        process = await asyncio.create_subprocess_exec(
            self.gemini_cmd,
            *args,
            cwd=str(repo),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ,
        )

        try:
            stdout_b, stderr_b = await asyncio.wait_for(process.communicate(), timeout=self.timeout_s)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError(f"gemini timed out after {self.timeout_s}s")

        stdout_text = stdout_b.decode() if stdout_b else ""
        stderr_text = stderr_b.decode() if stderr_b else ""
        combined = stdout_text + (("\n" + stderr_text) if stderr_text else "")

        if process.returncode != 0:
            raise RuntimeError(f"gemini failed (rc={process.returncode}). Output:\n{combined}")

        json_block = extract_between(combined, _BEGIN_JSON, _END_JSON)
        if not json_block:
            raise ValueError("gemini output missing iteration JSON markers")
        # Extract patch first
        diff_block = extract_between(combined, _BEGIN_DIFF, _END_DIFF)
        patch_diff = None
        if diff_block and diff_block.strip() != "NO_PATCH":
            patch_diff = diff_block.strip() + "\n"

        normalized_json_str = normalize_iteration_json(json_block)
        it = json.loads(normalized_json_str)

        # Apply defaults manually if needed, or trust normalize?
        # normalize_iteration_json already ensures schema.
        # But we might want to override track/iteration to be safe?
        it["track"] = track
        it["iteration"] = iteration
        if patch_diff:
            if "proposed_changes" not in it:
                it["proposed_changes"] = {}
            it["proposed_changes"]["has_patch"] = True
            
        return ProviderResult(
            text=combined,
            iteration_json=it,
            patch_diff=patch_diff,
            meta={"provider": "gemini", "model": self.model},
        )


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Gemini Provider CLI")
    parser.add_argument("--repo", required=True, help="Path to repo")
    parser.add_argument("--track", required=True, help="Track name")
    parser.add_argument("--iteration", type=int, default=1, help="Iteration")
    parser.add_argument("--role", default="debugger", help="Role")
    parser.add_argument("--directions", default="", help="Directions text")
    parser.add_argument("--context", default="", help="Context text")
    parser.add_argument("--blackboard", default="", help="Blackboard text")
    parser.add_argument("--model", default="gemini-3-pro", help="Gemini model")
    args = parser.parse_args()

    import asyncio
    
    async def main():
        provider = GeminiCliProvider(model=args.model)
        res = await provider.run_iteration(
            repo=Path(args.repo),
            track=args.track,
            iteration=args.iteration,
            role=args.role,
            directions=args.directions,
            context=args.context,
            blackboard=args.blackboard,
        )
        print(json.dumps({
            "text": res.text,
            "iteration_json": res.iteration_json,
            "patch_diff": res.patch_diff,
            "meta": res.meta
        }, indent=2, ensure_ascii=False))

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
