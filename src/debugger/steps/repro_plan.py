"""Repro plan step.

CONTRACT
- Inputs: ArtifactStore, Repo path, issue_text
- Outputs (required):
  - REPRO.md
- Invariants:
  - Always writes REPRO.md with "Classification", "Commands", "Expected vs Actual" sections
- Failure:
  - check() returns non-zero if REPRO.md is missing
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
        return 0 if res.ok else 1

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Repro Plan Step")
    parser.add_argument("--repo", required=True, help="Path to repo")
    parser.add_argument("--issue", required=True, help="Issue text")
    parser.add_argument("--out-dir", required=True, help="Output directory for artifacts")
    args = parser.parse_args()

    try:
        store = ArtifactStore(Path(args.out_dir))
        step = ReproPlan()
        step.run(store, Path(args.repo), args.issue)
        sys.exit(step.check(store, Path(args.repo)))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
