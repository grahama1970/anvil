
import pytest
from pathlib import Path
from anvil.artifacts.store import ArtifactStore
from anvil.steps.judge import Judge
from anvil.config import TrackConfig

def test_judge_role_aware_scoring(tmp_path):
    """Judge should penalize fixer tracks heavily for missing patches, but breakers less so."""
    store = ArtifactStore(tmp_path)
    
    # Track Fixer: No patch
    t_f = tmp_path / "tracks" / "fixer_track"
    (t_f / "iter_01").mkdir(parents=True)
    # No patch
    
    # Track Breaker: No patch
    t_b = tmp_path / "tracks" / "breaker_track"
    (t_b / "iter_01").mkdir(parents=True)
    # No patch
    
    judge = Judge()
    
    # Using explicit tracks_config
    tracks_config = {
        "fixer_track": TrackConfig(name="fixer_track", role="fixer", provider="manual"),
        "breaker_track": TrackConfig(name="breaker_track", role="breaker", provider="manual"),
    }
    
    decision = judge.run(
        store, 
        candidate_tracks=["fixer_track", "breaker_track"], 
        disqualified=[],
        tracks_config=tracks_config
    )
    scores = decision.scores
    
    # Fixer: 0 (conf) - 50 (no patch penalty) = -50
    # Breaker: 0 (conf) - 10 (no patch penalty) = -10
    
    assert scores["fixer_track"] == -50.0
    assert scores["breaker_track"] == -10.0
    assert scores["breaker_track"] > scores["fixer_track"]
