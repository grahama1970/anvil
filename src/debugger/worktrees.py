from __future__ import annotations

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
