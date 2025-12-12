from __future__ import annotations

"""Template initializer.

CONTRACT
- Inputs: Repo path
- Outputs (required):
  - Writes .dbg/tracks.yaml
  - Writes .dbg/verify_contract.yaml
  - Writes .dbg/issue.md
- Invariants:
  - Creates .dbg directory if missing
  - Does not overwrite existing files (by default)
- Failure:
  - Raises OSError on permission issues
"""

from pathlib import Path

from .util.paths import copy_template, ensure_dir


def write_templates(repo: Path, force: bool = False) -> None:
    dbg_dir = repo / ".dbg"
    ensure_dir(dbg_dir)

    copy_template("tracks.yaml", dbg_dir / "tracks.yaml", overwrite=force)
    copy_template("verify_contract.yaml", dbg_dir / "verify_contract.yaml", overwrite=force)
    copy_template("issue.md", dbg_dir / "issue.md", overwrite=force)
