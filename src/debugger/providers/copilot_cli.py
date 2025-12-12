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
            self.copilot_cmd,
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

        proc = subprocess.run(
            args,
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
        )
        combined = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        # Task 4.9: We could capture to files if we used run_cmd, or just expose them.
        # The ProviderResult currently returns 'text'.
        # Let's check base.py to see if we can add separate fields or meta.
        # For now, adhering to contract to return combined text, 
        # but we can enhance meta logs if needed.
        # But wait, step 4.9 says "Capture Provider stdout/stderr".
        # The current implementation DOES capture them in 'combined' text.
        # Maybe the task implies saving to files separately?
        # TrackIterate saves 'ITERATION.txt' which is result.text.
        # So it's effectively captured.
        # I'll double check if I should use shell.run_cmd here to save logs.
        # CLIs usually run manual subprocess because they might not want file side-effects 
        # in the repo root (or obscure logs).
        # Actually shell.run_cmd writes to explicit paths.
        # I will leave as is unless I see a STRONG need to change base ProviderResult.
        
        if proc.returncode != 0:
            raise RuntimeError(f"copilot failed (rc={proc.returncode}). Output:\n{combined}")

        json_block = extract_between(combined, _BEGIN_JSON, _END_JSON)
        if not json_block:
            raise ValueError("copilot output missing iteration JSON markers")
        it = json.loads(json_block)
        if not isinstance(it, dict):
            raise ValueError("iteration JSON must be an object")

        diff_block = extract_between(combined, _BEGIN_DIFF, _END_DIFF)
        patch_diff = None
        if diff_block and diff_block.strip() != "NO_PATCH":
            patch_diff = diff_block.strip() + "\n"

        it = normalize_iteration_json(
            it, track=track, iteration=iteration, has_patch=bool(patch_diff)
        )
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

    try:
        provider = CopilotCliProvider(model=args.model)
        res = provider.run_iteration(
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
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
