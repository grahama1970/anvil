"""Tests for harden mode functionality."""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from anvil.config import RunConfig, TrackConfig, TrackBudget
from anvil.orchestrator import run_harden_session
from anvil.artifacts.store import ArtifactStore


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a minimal git repo for testing."""
    import subprocess
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text('def hello():\n    return "world"\n')
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True, check=True)
    return repo


def test_harden_session_writes_run_meta(tmp_repo, tmp_path):
    """Harden session should write RUN.json with mode=harden."""
    artifacts_dir = tmp_path / "artifacts"
    
    cfg = RunConfig(
        repo_path=tmp_repo,
        run_id="test-harden-001",
        artifacts_root=artifacts_dir,
        tracks_file=None,
        issue_text="Find vulnerabilities",
        mode="harden",
    )
    
    with patch("anvil.orchestrator.WorktreeManager") as MockWT, \
         patch("anvil.orchestrator.TrackIterate") as MockTI, \
         patch("anvil.orchestrator.Verify") as MockVerify:
        
        MockWT.return_value.create_worktrees = MagicMock()
        MockWT.return_value.create_worktrees = MagicMock()
        MockWT.return_value.write_worktree_contracts = MagicMock()
        from anvil.worktrees import WorktreeValidation
        MockWT.return_value.validate_worktrees_ready.return_value = WorktreeValidation(ok_tracks=[], failed={})
        MockWT.return_value._is_git_repo.return_value = True
        
        mock_iter = MockTI.return_value
        mock_iter.run = AsyncMock()
        mock_iter.check = MagicMock(return_value=0)
        
        MockVerify.return_value.run = MagicMock()
        
        result = asyncio.run(run_harden_session(cfg))
    
    assert result.status in ("DONE", "FAIL")
    
    # Check RUN.json was written
    run_json = result.run_dir / "RUN.json"
    assert run_json.exists()
    
    import json
    data = json.loads(run_json.read_text())
    assert data["mode"] == "harden"
    assert data["run_id"] == "test-harden-001"


def test_harden_session_creates_harden_md(tmp_repo, tmp_path):
    """Harden session should create HARDEN.md report."""
    artifacts_dir = tmp_path / "artifacts"
    
    cfg = RunConfig(
        repo_path=tmp_repo,
        run_id="test-harden-002",
        artifacts_root=artifacts_dir,
        tracks_file=None,
        issue_text=None,
        mode="harden",
    )
    
    with patch("anvil.orchestrator.WorktreeManager") as MockWT, \
         patch("anvil.orchestrator.TrackIterate") as MockTI, \
         patch("anvil.orchestrator.Verify") as MockVerify:
        
        MockWT.return_value.create_worktrees = MagicMock()
        MockWT.return_value.create_worktrees = MagicMock()
        MockWT.return_value.write_worktree_contracts = MagicMock()
        from anvil.worktrees import WorktreeValidation
        MockWT.return_value.validate_worktrees_ready.return_value = WorktreeValidation(ok_tracks=[], failed={})
        MockWT.return_value._is_git_repo.return_value = True
        
        mock_iter = MockTI.return_value
        mock_iter.run = AsyncMock()
        mock_iter.check = MagicMock(return_value=0)
        
        MockVerify.return_value.run = MagicMock()
        
        result = asyncio.run(run_harden_session(cfg))
    
    # Check HARDEN.md was written
    harden_md = result.run_dir / "HARDEN.md"
    assert harden_md.exists()
    
    content = harden_md.read_text()
    assert "# HARDEN Report" in content
    assert "Findings by Track" in content


def test_harden_session_runs_baseline_verify(tmp_repo, tmp_path):
    """Harden session should run baseline verification."""
    artifacts_dir = tmp_path / "artifacts"
    
    cfg = RunConfig(
        repo_path=tmp_repo,
        run_id="test-harden-003",
        artifacts_root=artifacts_dir,
        tracks_file=None,
        issue_text=None,
        mode="harden",
    )
    
    with patch("anvil.orchestrator.WorktreeManager") as MockWT, \
         patch("anvil.orchestrator.TrackIterate") as MockTI, \
         patch("anvil.orchestrator.Verify") as MockVerify:
        
        MockWT.return_value.create_worktrees = MagicMock()
        MockWT.return_value.create_worktrees = MagicMock()
        MockWT.return_value.write_worktree_contracts = MagicMock()
        from anvil.worktrees import WorktreeValidation
        MockWT.return_value.validate_worktrees_ready.return_value = WorktreeValidation(ok_tracks=[], failed={})
        MockWT.return_value._is_git_repo.return_value = True
        
        mock_iter = MockTI.return_value
        mock_iter.run = AsyncMock()
        mock_iter.check = MagicMock(return_value=0)
        
        mock_verify = MockVerify.return_value
        mock_verify.run = MagicMock()
        
        asyncio.run(run_harden_session(cfg))
        
        # Verify was called (baseline verification)
        mock_verify.run.assert_called()


def test_harden_public_api_exists():
    """Test that the simple public API for harden exists."""
    import anvil
    
    assert hasattr(anvil, "harden")
    assert callable(anvil.harden)


def test_harden_api_signature():
    """Test that harden() has the expected signature."""
    import anvil
    import inspect
    
    sig = inspect.signature(anvil.harden)
    params = list(sig.parameters.keys())
    
    assert "repo" in params
    assert "focus" in params
    assert "run_id" in params
    assert "tracks_file" in params

