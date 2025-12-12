"""Apply step.

CONTRACT
- Applies the winning patch to the main repo (not the worktree).
- Outputs:
  - APPLY.md (what was applied)
  - logs/apply.stdout.log, logs/apply.stderr.log
- Failure:
  - If patch cannot be applied, exit code != 0 and APPLY.md must explain.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..artifacts.store import ArtifactStore
from ..util.shell import run_cmd


@dataclass
class Apply:
    name: str = "apply"

    def run(self, store: ArtifactStore, repo: Path, patch_path: Path) -> int:
        is_git_repo = (repo / ".git").exists() or (repo / ".git").is_file()
        res = run_cmd(
            cmd=f'git apply --whitespace=nowarn "{patch_path}"',
            cwd=repo,
            stdout_path=store.path("logs", "apply.stdout.log"),
            stderr_path=store.path("logs", "apply.stderr.log"),
            timeout_s=60,
        )
        md = ["# APPLY", "", f"Patch: `{patch_path}`", "", f"Exit: {res.returncode}", ""]
        if not is_git_repo:
            md += [
                "",
                "Note: repo does not look like a git repo (missing `.git`); `git apply` may fail.",
                "",
            ]
        store.write_text("APPLY.md", "\n".join(md))
        return res.returncode
