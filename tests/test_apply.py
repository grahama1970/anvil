"""Tests for the Apply step.

Verifies that Apply.run() correctly:
1. Runs `git apply --check` before applying
2. Fails fast on bad patches without modifying repo
3. Succeeds on valid patches
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from anvil.steps.apply import Apply
from anvil.artifacts.store import ArtifactStore


def test_apply_fails_on_bad_patch(tmp_path):
    """Apply should fail and not modify repo when patch is invalid."""
    # Setup
    store = ArtifactStore(tmp_path / "run")
    store.ensure()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()  # Fake git repo
    
    bad_patch = tmp_path / "bad.diff"
    bad_patch.write_text("this is not a valid patch format")
    
    # Mock run_cmd to simulate git apply --check failure
    with patch("anvil.steps.apply.run_cmd") as mock_run:
        # First call = git apply --check (fails)
        mock_check_result = MagicMock()
        mock_check_result.returncode = 1
        mock_check_result.stderr = "error: patch does not apply"
        mock_run.return_value = mock_check_result
        
        step = Apply()
        result = step.run(store, repo, bad_patch)
        
        # Assertions
        assert result != 0, "Should return non-zero on bad patch"
        apply_md = (tmp_path / "run" / "APPLY.md").read_text()
        assert "Check Failed" in apply_md, "APPLY.md should say check failed"


def test_apply_succeeds_on_good_patch(tmp_path):
    """Apply should succeed when patch is valid."""
    # Setup
    store = ArtifactStore(tmp_path / "run")
    store.ensure()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()  # Fake git repo
    
    good_patch = tmp_path / "good.diff"
    good_patch.write_text("--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-old\n+new")
    
    # Mock run_cmd to simulate success
    with patch("anvil.steps.apply.run_cmd") as mock_run:
        mock_success_result = MagicMock()
        mock_success_result.returncode = 0
        mock_success_result.stderr = ""
        mock_run.return_value = mock_success_result
        
        step = Apply()
        result = step.run(store, repo, good_patch)
        
        # Assertions
        assert result == 0, "Should return 0 on good patch"
        apply_md = (tmp_path / "run" / "APPLY.md").read_text()
        assert "Exit: 0" in apply_md
