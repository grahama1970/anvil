"""GitHub Copilot CLI provider.

CONTRACT
- Inputs: Repo, track, iteration, role, directions, context
- Outputs (required):
  - ProviderResult with parsed JSON and optional patch
- Invariants:
  - Invokes `copilot` CLI with specified model
  - Enforces strict BEGIN_ITERATION_JSON markers
  - Normalizes output JSON to ensure minimum schema structure
- Failure:
  - Raises RuntimeError if copilot CLI fails or returns non-zero
  - Raises ValueError if output format is invalid
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
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
class CopilotCliProvider(Provider):
    copilot_cmd: str = "copilot"
    model: str = "gpt-5"
    stream: str = "off"
    timeout_s: int = 600

    # Optional knobs (can be provided via TrackConfig.provider_options)
    no_color: bool = True
    no_custom_instructions: bool = True
    allow_all_paths: bool = False
    allow_all_tools: bool = False
    add_dirs: list[str] = field(default_factory=list)
    allow_tools: list[str] = field(default_factory=list)
    deny_tools: list[str] = field(default_factory=list)

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
        if which(self.copilot_cmd) is None:
            raise RuntimeError("copilot CLI not found in PATH")

        prompt = build_prompt(
            track=track,
            iteration=iteration,
            role=role,
            directions=directions,
            context=context,
            blackboard=blackboard,
        )

        args: list[str] = [
            "--model",
            self.model,
            "--stream",
            self.stream,
            "-p",
            prompt,
        ]
        if self.no_color:
            args.append("--no-color")
        if self.no_custom_instructions:
            args.append("--no-custom-instructions")
        if self.allow_all_paths:
            args.append("--allow-all-paths")
        if self.allow_all_tools:
            args.append("--allow-all-tools")
        for d in self.add_dirs:
            args.extend(["--add-dir", d])
        for t in self.allow_tools:
            args.extend(["--allow-tool", t])
        for t in self.deny_tools:
            args.extend(["--deny-tool", t])

        import asyncio
        import os

        process = await asyncio.create_subprocess_exec(
            self.copilot_cmd,
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
            raise RuntimeError(f"copilot timed out after {self.timeout_s}s")

        stdout_text = stdout_b.decode() if stdout_b else ""
        stderr_text = stderr_b.decode() if stderr_b else ""
        combined = stdout_text + (("\n" + stderr_text) if stderr_text else "")

        if process.returncode != 0:
            raise RuntimeError(f"copilot failed (rc={process.returncode}). Output:\n{combined}")

        json_block = extract_between(combined, _BEGIN_JSON, _END_JSON)
        if not json_block:
            raise ValueError("copilot output missing iteration JSON markers")
        diff_block = extract_between(combined, _BEGIN_DIFF, _END_DIFF)
        patch_diff = None
        if diff_block and diff_block.strip() != "NO_PATCH":
            patch_diff = diff_block.strip() + "\n"

        # Validate/Normalize JSON (robustly)
        normalized_str = normalize_iteration_json(json_block)
        it = json.loads(normalized_str)
        
        # Inject/Fix metadata that normalize might not know about
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
            meta={"provider": "copilot", "model": self.model},
        )


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Copilot Provider CLI")
    parser.add_argument("--repo", required=True, help="Path to repo")
    parser.add_argument("--track", required=True, help="Track name")
    parser.add_argument("--iteration", type=int, default=1, help="Iteration")
    parser.add_argument("--role", default="debugger", help="Role")
    parser.add_argument("--directions", default="", help="Directions text")
    parser.add_argument("--context", default="", help="Context text")
    parser.add_argument("--blackboard", default="", help="Blackboard text")
    parser.add_argument("--model", default="gpt-5", help="Copilot model")
    args = parser.parse_args()

    import asyncio
    
    async def main():
        provider = CopilotCliProvider(model=args.model)
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
