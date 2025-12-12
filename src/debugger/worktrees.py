from __future__ import annotations

"""Worktree management.

CONTRACT
- Inputs: Repo path, list of track names
- Outputs (required):
  - Git worktrees at .dbg/worktrees/<run_id>/<track>
  - CONTRACT.md in each worktree root
- Invariants:
  - Each track gets a dedicated branch dbg/<run_id>/<track>
  - Best-effort: warns but does not crash if non-git repo or git command fails
- Failure:
  - Logs warnings on git errors
"""

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from .artifacts.store import ArtifactStore
from .config import TrackConfig
from .util.shell import run_cmd


@dataclass
class WorktreeManager:
    repo: Path
    store: ArtifactStore

    def _is_git_repo(self) -> bool:
        return (self.repo / ".git").exists() or (self.repo / ".git").is_file()

    def _worktrees_root(self) -> Path:
        return self.repo / ".dbg" / "worktrees" / self.store.run_dir.name

    def create_worktrees(self, tracks: list[str]) -> None:
        """Create one git worktree per track.

        CONTRACT
        - Worktrees live under <repo>/.dbg/worktrees/<run_id>/<track>
        - Each worktree is on a branch dbg/<run_id>/<track>
        - If worktrees already exist, this is a no-op.
        """
        if not self._is_git_repo():
            logger.warning("Repo is not a git repo; skipping worktree creation.")
            return

        root = self._worktrees_root()
        root.mkdir(parents=True, exist_ok=True)

        for t in tracks:
            wt_dir = root / t
            branch = f"dbg/{self.store.run_dir.name}/{t}"
            if wt_dir.exists():
                continue
            
            # Use 'git branch --list' to check for conflicts (safer than relying on error)
            # Otherwise 'git worktree add' might fail with "already exists" but having checking is better.
            branch_check = run_cmd(
                f"git branch --list {branch}", 
                cwd=self.repo,
                timeout_s=5
            )
            stdout_content = branch_check.stdout_path.read_text(encoding="utf-8").strip() if branch_check.stdout_path and branch_check.stdout_path.exists() else ""
            if stdout_content:
                logger.warning(f"Branch {branch} already exists! Skipping worktree creation to avoid conflict.")
                continue

            # Create worktree on a new branch from current HEAD.
            cmd = f'git worktree add -b "{branch}" "{wt_dir}"'
            res = run_cmd(
                cmd=cmd,
                cwd=self.repo,
                stdout_path=self.store.path("logs", f"worktree_{t}.stdout.log"),
                stderr_path=self.store.path("logs", f"worktree_{t}.stderr.log"),
                timeout_s=60,
            )
            if res.returncode != 0:
                logger.warning(f"Failed to create worktree {t} (rc={res.returncode}); see logs.")

    def write_worktree_contracts(self, tracks: list[TrackConfig]) -> None:
        root = self._worktrees_root()
        for t in tracks:
            wt_dir = root / t.name
            if not wt_dir.exists():
                continue
            contract = [
                f"# CONTRACT — Worktree {t.name}",
                "",
                "## Purpose",
                f"- role: {t.role}",
                f"- provider: {t.provider}",
                f"- model: {t.model or 'null'}",
                "",
                "## Required artifacts (written to run artifacts, not necessarily committed)",
                f"- tracks/{t.name}/iter_XX/ITERATION.json",
                f"- tracks/{t.name}/iter_XX/ITERATION.txt",
                "",
                "## Disqualification",
                "- Missing required artifacts",
                "- Not running check gates",
                "- Editing outside this worktree",
                "- Claiming verification without logs",
                "",
            ]
            (wt_dir / "CONTRACT.md").write_text("\n".join(contract), encoding="utf-8")


if __name__ == "__main__":
    import argparse
    import sys

    from .config import load_tracks_file

    parser = argparse.ArgumentParser(description="Worktree Manager CLI")
    parser.add_argument("--repo", required=True, help="Path to repo")
    parser.add_argument("--run-dir", required=True, help="Path to run directory")
    parser.add_argument("--tracks-file", required=True, help="Path to tracks.yaml")
    args = parser.parse_args()

    try:
        store = ArtifactStore(Path(args.run_dir))
        wm = WorktreeManager(Path(args.repo), store)
        cfg = load_tracks_file(Path(args.tracks_file))
        tracks = [t.name for t in cfg.tracks]
        wm.create_worktrees(tracks)
        wm.write_worktree_contracts(cfg.tracks)
        print(f"Worktrees created for {tracks}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
