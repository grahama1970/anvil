"""Verification step.

CONTRACT
- Inputs: ArtifactStore, Repo path, .dbg/verify_contract.yaml
- Outputs (required):
  - VERIFY.md
  - logs/verify.commands.json
- Outputs (optional):
  - logs/verify.<name>.stdout.log
  - logs/verify.<name>.stderr.log
- Invariants:
  - Runs all commands in valid YAML contract
  - Records pass/fail status in VERIFY.md
- Failure:
  - check() returns 2 if VERIFY.md or command logs missing
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..artifacts.store import ArtifactStore
from ..contracts.validate import check_required_artifacts
from ..util.paths import safe_filename
from ..util.shell import run_cmd


@dataclass
class Verify:
    name: str = "verify"

    def _load_contract(self, repo: Path) -> dict[str, Any]:
        p = repo / ".dbg" / "verify_contract.yaml"
        if p.exists():
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return {"schema_version": 1, "commands": []}

    def run(self, store: ArtifactStore, repo: Path) -> None:
        contract = self._load_contract(repo)
        commands = contract.get("commands", []) or []
        ran: list[dict[str, Any]] = []
        failures: list[str] = []

        for c in commands:
            name = str(c.get("name", "cmd"))
            safe_name = safe_filename(name, default="cmd")
            cmd = str(c.get("cmd", ""))
            required = bool(c.get("required", False))
            if not cmd:
                continue

            res = run_cmd(
                cmd=cmd,
                cwd=repo,
                stdout_path=store.path("logs", f"verify.{safe_name}.stdout.log"),
                stderr_path=store.path("logs", f"verify.{safe_name}.stderr.log"),
                timeout_s=600,
            )
            # Task 4.10: Capture duration and bytes
            ran.append({
                "name": name, 
                "cmd": cmd, 
                "required": required, 
                "exit": res.returncode,
                "elapsed_s": res.elapsed_s,
                "stdout_bytes": res.stdout_bytes,
                "stderr_bytes": res.stderr_bytes,
            })
            if required and res.returncode != 0:
                failures.append(name)

        store.write_json(
            "logs/verify.commands.json", {"schema_version": 1, "ran": ran, "failures": failures}
        )

        md = ["# VERIFY", ""]
        if not commands:
            md += ["No verify_contract.yaml commands configured.", ""]
        else:
            md += ["## Commands", ""]
            for r in ran:
                md.append(
                    f"- `{r['name']}` exit={r['exit']} required={r['required']} cmd: `{r['cmd']}`"
                )
            md.append("")
        if failures:
            md += ["## Result", "", f"FAIL (required failures: {', '.join(failures)})", ""]
        else:
            md += ["## Result", "", "PASS", ""]

        store.write_text("VERIFY.md", "\n".join(md))

    def check(self, store: ArtifactStore, repo: Path) -> int:
        res = check_required_artifacts(store.run_dir, ["VERIFY.md", "logs/verify.commands.json"])
        store.write_json("CHECK_verify.json", res.model_dump())
        return 0 if res.ok else 1

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Verify Step")
    parser.add_argument("--repo", required=True, help="Path to repo")
    parser.add_argument("--out-dir", required=True, help="Output directory for artifacts")
    args = parser.parse_args()

    try:
        store = ArtifactStore(Path(args.out_dir))
        step = Verify()
        step.run(store, Path(args.repo))
        sys.exit(step.check(store, Path(args.repo)))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
