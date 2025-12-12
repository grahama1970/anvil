"""Tests for ReproAssess step."""

import json
from pathlib import Path

import pytest

from anvil.artifacts.store import ArtifactStore
from anvil.steps.repro_assess import ReproAssess, ReproMode


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Create a temp repo structure."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


@pytest.fixture
def store(tmp_path: Path) -> ArtifactStore:
    """Create temp artifact store."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    return ArtifactStore(run_dir)


def test_repro_assess_detects_pytest(temp_repo: Path, store: ArtifactStore):
    """Test detection of pytest infrastructure."""
    # Create pyproject.toml
    (temp_repo / "pyproject.toml").write_text("[project]\nname = 'test'")
    # Create tests dir
    (temp_repo / "tests").mkdir()
    (temp_repo / "tests" / "test_example.py").write_text("def test_foo(): pass")
    
    step = ReproAssess()
    result = step.run(store, temp_repo, issue_text="")
    
    assert result.mode == ReproMode.AUTO
    assert "pytest" in result.commands[0].lower()
    assert step.check(store) == 0


def test_repro_assess_detects_repro_script(temp_repo: Path, store: ArtifactStore):
    """Test detection of repro scripts."""
    (temp_repo / "repro.sh").write_text("#!/bin/bash\necho test")
    
    step = ReproAssess()
    result = step.run(store, temp_repo, issue_text="")
    
    assert result.mode == ReproMode.AUTO
    assert "repro.sh" in result.commands[0]


def test_repro_assess_detects_npm_tests(temp_repo: Path, store: ArtifactStore):
    """Test detection of npm test script."""
    pkg = {"name": "test", "scripts": {"test": "jest"}}
    (temp_repo / "package.json").write_text(json.dumps(pkg))
    
    step = ReproAssess()
    result = step.run(store, temp_repo, issue_text="")
    
    assert result.mode == ReproMode.AUTO
    assert "npm test" in result.commands


def test_repro_assess_detects_makefile(temp_repo: Path, store: ArtifactStore):
    """Test detection of Makefile test target."""
    (temp_repo / "Makefile").write_text("test:\n\tpytest")
    
    step = ReproAssess()
    result = step.run(store, temp_repo, issue_text="")
    
    assert result.mode == ReproMode.AUTO
    assert "make test" in result.commands


def test_repro_assess_defaults_to_manual(temp_repo: Path, store: ArtifactStore):
    """Test default to MANUAL when no automation found."""
    step = ReproAssess()
    result = step.run(store, temp_repo, issue_text="")
    
    assert result.mode == ReproMode.MANUAL
    assert result.confidence < 0.5


def test_repro_assess_writes_artifacts(temp_repo: Path, store: ArtifactStore):
    """Test that artifacts are written."""
    (temp_repo / "pyproject.toml").write_text("[project]\nname = 'test'")
    (temp_repo / "tests").mkdir()
    
    step = ReproAssess()
    step.run(store, temp_repo, issue_text="")
    
    assert store.path("REPRO_ASSESS.json").exists()
    assert store.path("REPRO_ASSESS.md").exists()
    
    data = json.loads(store.path("REPRO_ASSESS.json").read_text())
    assert data["repro_mode"] == "AUTO"
    assert "commands" in data


def test_repro_assess_extracts_test_from_issue(temp_repo: Path, store: ArtifactStore):
    """Test extraction of specific test from issue text."""
    (temp_repo / "pyproject.toml").write_text("[project]\nname = 'test'")
    (temp_repo / "tests").mkdir()
    (temp_repo / "tests" / "test_foo.py").write_text("")
    
    step = ReproAssess()
    result = step.run(store, temp_repo, issue_text="The test_calculate_sum is failing")
    
    assert result.mode == ReproMode.AUTO
    # Should have specific test command first
    assert any("test_calculate_sum" in cmd for cmd in result.commands)
