"""anvil package.

Simple API for orchestrator agents:

    import anvil
    
    # Debug a known bug
    result = anvil.debug("/path/to/repo", "The login button crashes on click")
    
    # Harden a codebase (find vulnerabilities)
    result = anvil.harden("/path/to/repo")
"""

import asyncio
from pathlib import Path
from typing import Optional

from .config import RunConfig, TrackConfig
from .orchestrator import run_debug_session, run_harden_session
from .util.ids import new_run_id


def debug(
    repo: str | Path,
    issue: str,
    *,
    run_id: Optional[str] = None,
    tracks_file: Optional[str | Path] = None,
) -> dict:
    """Debug a known bug. Returns structured result.
    
    Args:
        repo: Path to git repository
        issue: Description of the bug to fix
        run_id: Optional custom run ID (auto-generated if not provided)
        tracks_file: Optional path to tracks.yaml config
    
    Returns:
        dict with keys: status, run_dir, winner, patches
    """
    repo_path = Path(repo).resolve()
    cfg = RunConfig(
        repo_path=repo_path,
        run_id=run_id or new_run_id(),
        artifacts_root=repo_path / ".dbg" / "runs",
        tracks_file=Path(tracks_file) if tracks_file else None,
        issue_text=issue,
        mode="debug",
    )
    result = asyncio.run(run_debug_session(cfg))
    
    # Find any patches generated
    patches = []
    for p in result.run_dir.glob("tracks/*/iter_*/PATCH.diff"):
        patches.append(str(p))
    
    return {
        "status": result.status,
        "run_dir": str(result.run_dir),
        "decision_file": str(result.decision_file) if result.decision_file else None,
        "patches": patches,
    }


def harden(
    repo: str | Path,
    *,
    focus: Optional[str] = None,
    run_id: Optional[str] = None,
    tracks_file: Optional[str | Path] = None,
) -> dict:
    """Harden a codebase - find vulnerabilities, missing tests, edge cases.
    
    Args:
        repo: Path to git repository
        focus: Optional focus area (e.g., "security", "error handling")
        run_id: Optional custom run ID
        tracks_file: Optional path to tracks.yaml config
    
    Returns:
        dict with keys: status, run_dir, findings, patches
    """
    repo_path = Path(repo).resolve()
    issue_text = focus or "Find vulnerabilities, missing tests, and edge cases."
    
    cfg = RunConfig(
        repo_path=repo_path,
        run_id=run_id or new_run_id(),
        artifacts_root=repo_path / ".dbg" / "runs",
        tracks_file=Path(tracks_file) if tracks_file else None,
        issue_text=issue_text,
        mode="harden",
    )
    result = asyncio.run(run_harden_session(cfg))
    
    # Find any patches generated
    patches = []
    for p in result.run_dir.glob("tracks/*/iter_*/PATCH.diff"):
        patches.append(str(p))
    
    # Read findings from HARDEN.md if exists
    harden_md = result.run_dir / "HARDEN.md"
    findings = harden_md.read_text() if harden_md.exists() else ""
    
    return {
        "status": result.status,
        "run_dir": str(result.run_dir),
        "findings": findings,
        "patches": patches,
    }


__all__ = [
    "debug",
    "harden", 
    "RunConfig", 
    "TrackConfig", 
    "run_debug_session", 
    "run_harden_session",
]

