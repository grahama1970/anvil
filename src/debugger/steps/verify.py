"""Verification step.

CONTRACT
- Reads verify contract from:
  - <repo>/.dbg/verify_contract.yaml if present
- Writes (required):
  - VERIFY.md
  - logs/verify.<name>.stdout.log
  - logs/verify.<name>.stderr.log
  - logs/verify.commands.json
- Success requires all commands marked required=true to exit 0.
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
            ran.append({"name": name, "cmd": cmd, "required": required, "exit": res.returncode})
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
        return res.exit_code
