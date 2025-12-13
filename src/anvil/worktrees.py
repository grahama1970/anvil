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
class WorktreeValidation:
    """Structured validation results for agent consumption."""
    ok_tracks: list[str]
    failed: dict[str, str]  # track -> reason


@dataclass
class WorktreeManager:
    repo: Path
    store: ArtifactStore

    def _is_git_repo(self) -> bool:
        return (self.repo / ".git").exists() or (self.repo / ".git").is_file()

    def _worktrees_root(self) -> Path:
        return self.repo / ".dbg" / "worktrees" / self.store.run_dir.name

    def get_worktree_path(self, track: str) -> Path:
        """Get the absolute path to a track's worktree."""
        return self._worktrees_root() / track
    
    def validate_worktrees_ready(self, tracks: list[str]) -> WorktreeValidation:
        """Validate worktrees exist and are git-healthy.
        
        Returns structured validation results with:
        - ok_tracks: list of validated tracks
        - failed: dict mapping track name to failure reason
        """
        ok_tracks = []
        failed = {}
        
        for track in tracks:
            wt_path = self.get_worktree_path(track)
            
            # Check 1: directory exists
            if not wt_path.exists():
                failed[track] = f"Worktree directory missing: {wt_path}"
                continue
            
            # Check 2: .git file exists (worktrees have .git file pointing to main repo)
            git_file = wt_path / ".git"
            if not git_file.exists():
                failed[track] = f"Missing .git file in worktree: {wt_path}"
                continue
            
            # Check 3: git status works (validates git health)
            status_check = run_cmd(
                f"git -C \"{wt_path}\" status",
                cwd=self.repo,
                timeout_s=10,
            )
            if status_check.returncode != 0:
                failed[track] = f"git status failed in worktree (rc={status_check.returncode})"
                continue
            
            # All checks passed
            ok_tracks.append(track)
        
        return WorktreeValidation(ok_tracks=ok_tracks, failed=failed)

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

    def _all_worktrees_root(self) -> Path:
        return self.repo / ".dbg" / "worktrees"

    def find_stale_worktrees(self) -> list[tuple[Path, str]]:
        """Find worktrees without corresponding run artifacts or that are very old.
        
        Returns:
            List of (worktree_path, run_id)
        """
        root = self._all_worktrees_root()
        if not root.exists():
            return []
            
        stale = []
        # Iterate over <repo>/.dbg/worktrees/<run_id>
        for run_dir in root.iterdir():
            if not run_dir.is_dir():
                continue
            
            run_id = run_dir.name
            
            # Check 1: Artifacts exist?
            # Default artifacts location relative to repo
            # (Note: artifacts_root might be elsewhere if configured via CLI, 
            # but we assume standard location for stale detection default)
            artifacts_run_dir = self.repo / ".dbg" / "runs" / run_id
            status_file = artifacts_run_dir / "RUN_STATUS.json"
            
            if not status_file.exists():
                # If we can't confirm run status in default location, check directory age
                from datetime import datetime, timedelta
                mtime = datetime.fromtimestamp(run_dir.stat().st_mtime)
                # Mark stale only if > 7 days old
                if mtime < datetime.now() - timedelta(days=7):
                    stale.append((run_dir, run_id))
            else:
                 # Check status content? Or just assume recent runs are valid?
                 # For now, this method is primarily for diagnosis. 
                 pass
            
        return stale

    def cleanup_stale_worktrees(self, older_than_days: int = 7) -> int:
        """Clean worktrees older than N days.
        
        Returns:
            Count of removed worktrees (tracks)
        """
        from datetime import datetime, timedelta
        import shutil
        
        if not self._is_git_repo():
            return 0
            
        root = self._all_worktrees_root()
        if not root.exists():
            return 0
            
        removed_count = 0
        threshold = datetime.now() - timedelta(days=older_than_days)
        
        for run_dir in root.iterdir():
            if not run_dir.is_dir():
                continue
                
            # Check modification time
            mtime = datetime.fromtimestamp(run_dir.stat().st_mtime)
            if mtime < threshold:
                # Expired run directory
                run_id = run_dir.name
                
                # Check for tracks inside
                tracks = []
                for t_dir in run_dir.iterdir():
                    if t_dir.is_dir():
                        tracks.append(t_dir.name)
                
                # Use cleanup logic (remove worktrees + branches)
                # We construct a temporary store just for path resolution if needed, 
                # but cleanup takes track names.
                # However, our instance's self.store points to CURRENT run.
                # We need to be careful. cleanup() uses self.store.run_dir.name to find branch!
                # So we can't reuse self.cleanup() easily for OTHER runs without hacks.
                
                # Manual cleanup implementation for stale run
                for t in tracks:
                    wt_dir = run_dir / t
                    branch = f"dbg/{run_id}/{t}"
                    
                    # 1. Remove worktree
                    if wt_dir.exists():
                        run_cmd(f'git worktree remove --force "{wt_dir}"', cwd=self.repo, timeout_s=30)
                    
                    # 2. Delete branch
                    run_cmd(f'git branch -D "{branch}"', cwd=self.repo, timeout_s=10)
                    
                    removed_count += 1
                
                # Remove run dir
                try:
                    shutil.rmtree(run_dir)
                except OSError:
                    pass
                    
        return removed_count

    def cleanup(self, tracks: list[str], archive: bool = False) -> None:
        """Remove worktrees and optionally archive branches.
        
        Uses `git worktree list --porcelain` to ensure we only remove valid worktrees
        and clean up orphaned metadata.
        """
        if not self._is_git_repo():
            logger.warning("Repo is not a git repo; skipping cleanup.")
            return

        # 1. Get canonical list of worktrees to avoid removing non-worktree dirs
        res = run_cmd("git worktree list --porcelain", cwd=self.repo, timeout_s=5)
        known_worktrees = set()
        if res.returncode == 0 and res.stdout_path and res.stdout_path.exists():
            content = res.stdout_path.read_text()
            for line in content.splitlines():
                if line.startswith("worktree "):
                    known_worktrees.add(Path(line[9:].strip()).resolve())

        root = self._worktrees_root()
        
        for t in tracks:
            wt_dir = (root / t).resolve()
            branch = f"dbg/{self.store.run_dir.name}/{t}"
            
            # Remove worktree
            # Case A: Git knows about it
            if wt_dir in known_worktrees:
                cmd = f'git worktree remove --force "{wt_dir}"'
                res = run_cmd(cmd, cwd=self.repo, timeout_s=30)
                if res.returncode != 0:
                    logger.warning(f"Failed to remove worktree {t}")
            # Case B: Directory exists but git doesn't know (orphaned folder)
            elif wt_dir.exists():
                import shutil
                try:
                    shutil.rmtree(wt_dir)
                    logger.info(f"Removed orphaned worktree directory: {wt_dir}")
                except OSError as e:
                    logger.warning(f"Failed to remove orphaned directory {wt_dir}: {e}")
            
            # Prune git worktree metadata (if any remains)
            run_cmd("git worktree prune", cwd=self.repo, timeout_s=10)

            # Archive or delete branch
            if archive:
                self._archive_branch(branch, t)
            else:
                # Delete branch
                cmd = f'git branch -D "{branch}"'
                run_cmd(cmd, cwd=self.repo, timeout_s=10)
        
        # Try to remove the worktrees root if empty
        if root.exists():
            try:
                root.rmdir()
            except OSError:
                pass  # Not empty, that's fine

    def _archive_branch(self, branch: str, track: str) -> None:
        """Rename a branch to archive/anvil-{run_id}-{track}-{timestamp}."""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"archive/anvil-{self.store.run_dir.name}-{track}-{timestamp}"
        
        # Check if branch exists
        check = run_cmd(f'git branch --list "{branch}"', cwd=self.repo, timeout_s=5)
        if check.stdout_path and check.stdout_path.exists():
            output = check.stdout_path.read_text().strip()
            if not output:
                logger.debug(f"Branch {branch} doesn't exist, nothing to archive")
                return
        
        # Rename branch
        cmd = f'git branch -m "{branch}" "{archive_name}"'
        res = run_cmd(cmd, cwd=self.repo, timeout_s=10)
        if res.returncode == 0:
            logger.info(f"Archived branch {branch} -> {archive_name}")
        else:
            logger.warning(f"Failed to archive branch {branch}")

    def list_archived_branches(self) -> list[str]:
        """List all archived debug branches."""
        res = run_cmd("git branch --list 'archive/anvil-*'", cwd=self.repo, timeout_s=5)
        if res.stdout_path and res.stdout_path.exists():
            output = res.stdout_path.read_text()
            return [b.strip().lstrip("* ") for b in output.splitlines() if b.strip()]
        return []


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
