
import pytest
from pathlib import Path
from anvil.artifacts.store import ArtifactStore
from anvil.steps.judge import Judge

def test_judge_prefers_verified(tmp_path):
    """Judge should prefer a track with PASS verification over one without."""
    store = ArtifactStore(tmp_path)
    
    # Track A: High confidence, Patch, No Verify (20 points patch)
    t_a = tmp_path / "tracks" / "track_a"
    (t_a / "iter_01").mkdir(parents=True)
    (t_a / "iter_01" / "ITERATION.json").write_text('{"confidence": 0.9}')
    (t_a / "iter_01" / "PATCH.diff").write_text("patch")
    
    # Track B: Lower confidence, Patch, Verify PASS (+20 patch + 10 exists + 40 pass)
    t_b = tmp_path / "tracks" / "track_b"
    (t_b / "iter_01").mkdir(parents=True)
    (t_b / "iter_01" / "ITERATION.json").write_text('{"confidence": 0.5}')
    (t_b / "iter_01" / "PATCH.diff").write_text("patch")
    (t_b / "iter_01" / "VERIFY.md").write_text("Integration tests: PASS")
    
    judge = Judge()
    judge.run(store, candidate_tracks=["track_a", "track_b"], disqualified=[])
    
    scorecard = store.read_json("SCORECARD.json")
    winner = scorecard["winner"]
    scores = scorecard["scores"]
    
    # Track B should win significantly
    # A ~= 0.9 * 100 + 20 = 110
    # B ~= 0.5 * 100 + 20 + 10 + 40 = 120
    assert winner == "track_b"
    assert scores["track_b"] > scores["track_a"]

def test_judge_penalizes_failed_verification(tmp_path):
    """Judge should penalize a track with FAIL verification."""
    store = ArtifactStore(tmp_path)
    
    # Track A: Patch only
    t_a = tmp_path / "tracks" / "track_a"
    (t_a / "iter_01").mkdir(parents=True)
    (t_a / "iter_01" / "ITERATION.json").write_text('{"confidence": 0.5}')
    (t_a / "iter_01" / "PATCH.diff").write_text("patch")
    
    # Track B: Patch + Verify FAIL
    t_b = tmp_path / "tracks" / "track_b"
    (t_b / "iter_01").mkdir(parents=True)
    (t_b / "iter_01" / "ITERATION.json").write_text('{"confidence": 0.5}')
    (t_b / "iter_01" / "PATCH.diff").write_text("patch")
    (t_b / "iter_01" / "VERIFY.md").write_text("Integration tests: FAIL")
    
    judge = Judge()
    judge.run(store, candidate_tracks=["track_a", "track_b"], disqualified=[])
    
    scorecard = store.read_json("SCORECARD.json")
    winner = scorecard["winner"]
    
    # Track A should win
    # A ~= 70
    # B ~= 70 + 10 - 40 = 40
    assert winner == "track_a"
