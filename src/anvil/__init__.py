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
        dict with keys: status, run_dir, winner, patch_file, patches
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
    
    # Parse decision to find winner
    winner = None
    if result.run_dir:
        import json
        try:
            scorecard = result.run_dir / "SCORECARD.json"
            if scorecard.exists():
                data = json.loads(scorecard.read_text())
                winner = data.get("winner")
        except Exception:
            pass

    # Find best patch (if winner exists, their patch; else first patch?)
    # README promises "patch_file". 
    patch_file = None
    if winner:
         # Try to find winner's patch
         # tracks/<winner>/iter_*/PATCH.diff
         # We want the LAST one usually?
         winner_patches = list(result.run_dir.glob(f"tracks/{winner}/iter_*/PATCH.diff"))
         if winner_patches:
             patch_file = str(sorted(winner_patches)[-1])
    
    # If no winner patch, but we have patches, maybe return one? 
    # But strictly, the return value implies the "result patch".
    # If no winner, patch_file is None.

    return {
        "status": result.status,
        "run_dir": str(result.run_dir),
        "decision_file": str(result.decision_file) if result.decision_file else None,
        "winner": winner,
        "patch_file": patch_file,
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
        # Harden mode uses "findings" more than single winner, but let's be consistent if possible
    }


__all__ = [
    "debug",
    "harden", 
    "RunConfig", 
    "TrackConfig", 
    "run_debug_session", 
    "run_harden_session",
]

