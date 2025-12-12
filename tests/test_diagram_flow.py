
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
from anvil.orchestrator import run_debug_session
from anvil.config import RunConfig, TrackConfig, TracksFileConfig

def test_verify_diagram_flow(tmp_path):
    """
    Verify the Logic of the Mermaid Diagram:
    Parallel Tracks (Approaches A & B) -> Artifacts -> Judge -> Winner.
    
    Scenario:
    - Track A ("Conservative"): Produces Patch A. Verifies PASS.
    - Track B ("Refactor"): Produces Patch B. Verifies FAIL.
    - Expected: Judge picks A.
    """
    asyncio.run(_async_diagram_flow(tmp_path))

async def _async_diagram_flow(tmp_path):
    # Setup Store/Repo
    repo = tmp_path / "repo"
    repo.mkdir()
    
    # We mock TrackIterate.run to simulate agents writing artifacts
    async def mock_agent_execution(*args, **kwargs):
        store = kwargs['store']
        track_name = kwargs['track']
        # Simulate Agent Work
        track_dir = store.path("tracks", track_name)
        iter_dir = track_dir / "iter_01"
        iter_dir.mkdir(parents=True, exist_ok=True)
        
        if track_name == "track_conservative":
            # Agent A: Good Patch
            (iter_dir / "ITERATION.json").write_text('{"confidence": 0.9, "status_signal": "DONE"}')
            (iter_dir / "PATCH.diff").write_text("conservative patch content")
            (iter_dir / "VERIFY.md").write_text("Tests: PASS")
        elif track_name == "track_refactor":
            # Agent B: Bad Patch (but ambitious)
            (iter_dir / "ITERATION.json").write_text('{"confidence": 0.6, "status_signal": "DONE"}')
            (iter_dir / "PATCH.diff").write_text("refactor patch content")
            (iter_dir / "VERIFY.md").write_text("Tests: FAIL")

    # Mock Dependencies
    with patch("anvil.orchestrator.TrackIterate") as MockStep, \
         patch("anvil.orchestrator.WorktreeManager"), \
         patch("anvil.orchestrator.Verify"), \
         patch("anvil.orchestrator.ReproPlan") as MockReproPlan, \
         patch("anvil.orchestrator.ContextBuilder") as MockCTX, \
         patch("anvil.orchestrator.Apply") as MockApply, \
         patch("anvil.orchestrator.load_tracks_file") as MockLoad:

        # Configure Checks to Pass
        MockCTX.return_value.check.return_value = 0
        MockReproPlan.return_value.check.return_value = 0
        
        # Configure Step Execution
        MockStep.return_value.run = AsyncMock(side_effect=mock_agent_execution)
        MockStep.return_value.check.return_value = 0
        
        # Configure Tracks
        tracks = [
            TrackConfig(name="track_conservative", role="dev", provider="manual", directions_profile="A"),
            TrackConfig(name="track_refactor", role="dev", provider="manual", directions_profile="B"),
        ]
        MockLoad.return_value = TracksFileConfig(tracks=tracks)
        
        # Setup Artifacts
        run_dir = tmp_path / "run_diagram"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "CONTEXT.md").write_text("context")
        
        dummy_tracks = tmp_path / "tracks.yaml"
        dummy_tracks.touch()
        
        cfg = RunConfig(
            run_id="run_diagram",
            repo_path=repo,
            artifacts_root=tmp_path,
            tracks_file=dummy_tracks,
            issue_text="bug",
            mode="debug"
        )
        
        # Execute Orchestrator (it calls Judge internally)
        # Note: We are NOT mocking Judge, we use Real Judge to verify selection logic!
        # But Judge requires ScoreComputer etc.
        # We need to ensure Judge dependencies work.
        # Judge reads artifacts. We wrote valid artifacts.
        
        result = await run_debug_session(cfg)
        
        # Assertion: Winner should be A ("conservative")
        # Check Run Result or Status
        
        store = result.run_dir # path
        # Re-read status
        import json
        status_json = json.loads((run_dir / "RUN_STATUS.json").read_text())
        print("Final Status:", status_json)
        
        # Verify Winner
        # The Orchestrator applies the winner patch.
        # We mocked Apply().run. Check if called with correct patch.
        
        # Check call args of Apply.run
        # args[0] is store, args[1] repo, patch_path=...
        
        assert MockApply.return_value.run.called
        call_args = MockApply.return_value.run.call_args
        patch_path = call_args.kwargs['patch_path']
        
        print(f"Winner Patch: {patch_path}")
        assert "track_conservative" in str(patch_path)
        assert "iter_01" in str(patch_path)

