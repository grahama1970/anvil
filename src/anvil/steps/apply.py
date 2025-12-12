"""Apply step.

CONTRACT
- Inputs: ArtifactStore, Repo path, patch path
- Outputs (required):
  - APPLY.md
  - logs/apply.stdout.log
  - logs/apply.stderr.log
- Invariants:
  - Applies patch using `git apply --whitespace=nowarn`
  - Records exit code in APPLY.md
- Failure:
  - If patch fails (exit != 0), APPLY.md records failure code but run() returns exit code
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
        
        # Task 4.7: Check first
        check_res = run_cmd(
            cmd=f'git apply --check --whitespace=nowarn "{patch_path}"',
            cwd=repo,
            stdout_path=store.path("logs", "apply_check.stdout.log"),
            stderr_path=store.path("logs", "apply_check.stderr.log"),
            timeout_s=30,
        )
        
        md_lines = ["# APPLY", "", f"Patch: `{patch_path}`"]
        
        if check_res.returncode != 0:
            md_lines.extend([
                "", 
                "## Check Failed", 
                "```text", 
                check_res.stderr.strip() if check_res.stderr else "See logs/apply_check.stderr.log",
                "```",
                f"Exit: {check_res.returncode}",
            ])
            store.write_text("APPLY.md", "\n".join(md_lines) + "\n")
            return check_res.returncode

        # If check passed, apply
        res = run_cmd(
            cmd=f'git apply --whitespace=nowarn "{patch_path}"',
            cwd=repo,
            stdout_path=store.path("logs", "apply.stdout.log"),
            stderr_path=store.path("logs", "apply.stderr.log"),
            timeout_s=60,
        )
        
        md_lines.extend(["", f"Exit: {res.returncode}", ""])
        if not is_git_repo:
            md_lines += [
                "",
                "Note: repo does not look like a git repo (missing `.git`); `git apply` may fail.",
                "",
            ]
        store.write_text("APPLY.md", "\n".join(md_lines) + "\n")
        return res.returncode

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Apply Step")
    parser.add_argument("--repo", required=True, help="Path to repo")
    parser.add_argument("--patch", required=True, help="Path to patch file")
    parser.add_argument("--out-dir", required=True, help="Output directory for artifacts")
    args = parser.parse_args()

    try:
        store = ArtifactStore(Path(args.out_dir))
        step = Apply()
        res = step.run(store, Path(args.repo), Path(args.patch))
        sys.exit(res)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
