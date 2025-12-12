from __future__ import annotations

from pathlib import Path

from .util.paths import copy_template, ensure_dir


def write_templates(repo: Path) -> None:
    dbg_dir = repo / ".dbg"
    ensure_dir(dbg_dir)

    copy_template("tracks.yaml", dbg_dir / "tracks.yaml")
    copy_template("verify_contract.yaml", dbg_dir / "verify_contract.yaml")
    copy_template("issue.md", dbg_dir / "issue.md")
