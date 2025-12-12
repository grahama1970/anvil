"""Repro plan step.

CONTRACT
- Outputs (required):
  - REPRO.md
- Purpose:
  - create a deterministic reproduction plan, or explicitly classify MANUAL/SEMI_AUTO.
- check() fails if REPRO.md missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..artifacts.store import ArtifactStore
from ..contracts.validate import check_required_artifacts


@dataclass
class ReproPlan:
    name: str = "repro_plan"

    def run(self, store: ArtifactStore, repo: Path, issue_text: str) -> None:
        md = [
            "# REPRO",
            "",
            "## Classification",
            "- Repro mode: AUTO | SEMI_AUTO | MANUAL (fill)",
            "",
            "## Commands",
            "```bash",
            "# fill commands to reproduce",
            "```",
            "",
            "## Expected vs Actual",
            "Expected:",
            "",
            "Actual:",
            "",
            "## Notes",
            "",
            "Issue reference:",
            "```text",
            issue_text.strip(),
            "```",
            "",
        ]
        store.write_text("REPRO.md", "\n".join(md))

    def check(self, store: ArtifactStore, repo: Path) -> int:
        res = check_required_artifacts(store.run_dir, ["REPRO.md"])
        store.write_json("CHECK_repro_plan.json", res.model_dump())
        return res.exit_code
