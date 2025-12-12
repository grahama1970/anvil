"""Claude Code CLI provider.

CONTRACT
- Inputs: Repo, track, iteration, role, directions, context, blackboard
- Outputs (required):
  - ProviderResult with parsed JSON and optional patch diff
- Invariants:
  - Invokes a local Claude CLI binary (default: `claude`)
  - Output must contain strict BEGIN_ITERATION_JSON/END_ITERATION_JSON markers
  - Patch diff must be between BEGIN_PATCH_DIFF/END_PATCH_DIFF
- Failure:
  - Raises RuntimeError if CLI fails or times out
  - Raises ValueError if output is missing markers or invalid JSON
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from ..util.shell import which
from .base import Provider, ProviderResult
from .common import build_prompt, extract_between, normalize_iteration_json

_BEGIN_JSON = "BEGIN_ITERATION_JSON"
_END_JSON = "END_ITERATION_JSON"
_BEGIN_DIFF = "BEGIN_PATCH_DIFF"
_END_DIFF = "END_PATCH_DIFF"


@dataclass
class ClaudeCliProvider(Provider):
    claude_cmd: str = "claude"
    timeout_s: int = 600
    # Allow passing extra args via config if needed (e.g. ["--expensive"])
    extra_args: list[str] = field(default_factory=list)

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
        if which(self.claude_cmd) is None:
            raise RuntimeError("claude CLI not found in PATH")

        prompt = build_prompt(
            track=track,
            iteration=iteration,
            role=role,
            directions=directions,
            context=context,
            blackboard=blackboard,
        )

        # Invocation: claude [extra_args] -p <prompt>
        # Adjust as needed for specific Claude CLI variants.
        argv = [self.claude_cmd]
        if self.extra_args:
            argv.extend(self.extra_args)
        argv.extend(["-p", prompt])

        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(repo),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ,
        )

        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=self.timeout_s)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(f"claude timed out after {self.timeout_s}s")

        stdout = stdout_b.decode() if stdout_b else ""
        stderr = stderr_b.decode() if stderr_b else ""
        combined = stdout + (("\n" + stderr) if stderr else "")

        if proc.returncode != 0:
            raise RuntimeError(f"claude failed (rc={proc.returncode}). Output:\n{combined}")

        json_block = extract_between(combined, _BEGIN_JSON, _END_JSON)
        if not json_block:
            raise ValueError("claude output missing iteration JSON markers")

        it_raw = json.loads(json_block)
        if not isinstance(it_raw, dict):
            raise ValueError("iteration JSON must be an object")

        diff_block = extract_between(combined, _BEGIN_DIFF, _END_DIFF)
        patch_diff = None
        if diff_block and diff_block.strip() != "NO_PATCH":
            patch_diff = diff_block.strip() + "\n"

        it = normalize_iteration_json(it_raw, track=track, iteration=iteration, has_patch=bool(patch_diff))
        return ProviderResult(
            text=combined,
            iteration_json=it,
            patch_diff=patch_diff,
            meta={"provider": "claude", "cmd": self.claude_cmd},
        )


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Claude Provider CLI")
    parser.add_argument("--repo", required=True, help="Path to repo")
    parser.add_argument("--track", required=True, help="Track name")
    parser.add_argument("--iteration", type=int, default=1, help="Iteration")
    parser.add_argument("--role", default="debugger", help="Role")
    parser.add_argument("--directions", default="", help="Directions text")
    parser.add_argument("--context", default="", help="Context text")
    parser.add_argument("--blackboard", default="", help="Blackboard text")
    parser.add_argument("--claude-cmd", default="claude", help="Claude CLI executable name")
    args = parser.parse_args()

    async def main() -> int:
        provider = ClaudeCliProvider(claude_cmd=args.claude_cmd)
        res = await provider.run_iteration(
            repo=Path(args.repo),
            track=args.track,
            iteration=args.iteration,
            role=args.role,
            directions=args.directions,
            context=args.context,
            blackboard=args.blackboard,
        )
        print(
            json.dumps(
                {
                    "text": res.text,
                    "iteration_json": res.iteration_json,
                    "patch_diff": res.patch_diff,
                    "meta": res.meta,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
