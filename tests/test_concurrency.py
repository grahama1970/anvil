
import asyncio
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from anvil.orchestrator import run_debug_session
from anvil.config import RunConfig, TrackConfig

@pytest.mark.timeout(5)
def test_parallel_tracks_execution(tmp_path):
    """Verify that multiple tracks run concurrently (total time < sum of parts)."""
    asyncio.run(_async_run_parallel(tmp_path))

async def _async_run_parallel(tmp_path):
    # Mock TrackIterate using a context code pattern that delays
    async def mock_run_side_effect(*args, **kwargs):
        await asyncio.sleep(1.0) # sleep 1s
        return None

    # We need to patch TrackIterate.run specifically
    # And also mock the other dependencies of run_debug_session
    
    with patch("anvil.orchestrator.TrackIterate") as MockStep:
        instance = MockStep.return_value
        instance.run = AsyncMock(side_effect=mock_run_side_effect)
        
        # Also patch: create_worktrees, write_worktree_contracts, verify_baseline, ReproPlan, ContextBuilder, and load_tracks_file
        with patch("anvil.orchestrator.WorktreeManager") as MockWT, \
             patch("anvil.orchestrator.Verify") as MockVerify, \
             patch("anvil.orchestrator.ReproPlan") as MockReproPlan, \
             patch("anvil.orchestrator.ContextBuilder") as MockCTX, \
             patch("anvil.orchestrator.Judge") as MockJudge, \
             patch("anvil.orchestrator.load_tracks_file") as MockLoadTracks, \
             patch("anvil.orchestrator.EventLog") as MockEventLog:
             
            # Configure mocks to pass checks
            MockCTX.return_value.check.return_value = 0
            MockReproPlan.return_value.check.return_value = 0
            
            # Setup mocked tracks
            from anvil.config import TracksFileConfig
            mock_tracks = [
                TrackConfig(name="track_1", role="dev", provider="manual", directions_profile="fake"),
                TrackConfig(name="track_2", role="dev", provider="manual", directions_profile="fake")
            ]
            MockLoadTracks.return_value = TracksFileConfig(tracks=mock_tracks)

            # Ensure tracks file exists so _load_tracks calls our mock
            dummy_yaml = tmp_path / "dummy.yaml"
            dummy_yaml.touch()

            # Ensure CONTEXT.md exists so orchestrator doesn't crash reading it
            run_dir = tmp_path / "test_concurrency"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "CONTEXT.md").write_text("mock context")

            # Configure RunConfig (tracks_file is required to trigger loading)
            cfg = RunConfig(
                run_id="test_concurrency",
                repo_path="/tmp/fake",
                artifacts_root=tmp_path,
                tracks_file=dummy_yaml, 
                issue_text="fake",
                mode="debug"
            )
            
            start = time.time()
            result = await run_debug_session(cfg)
            duration = time.time() - start
            
            # Debug: Print events if count is 0
            if instance.run.call_count == 0:
                print("Events captured:")
                for call in MockEventLog.return_value.emit.call_args_list:
                    print(call)

            # Assertions
            # 1. Did we run both?
            assert instance.run.call_count == 2
            
            # 2. Was it parallel? (1s sleep * 2 tracks = 2s sequential. Parallel should be ~1s)
            print(f"Duration: {duration:.2f}s")
            assert duration < 1.5, f"Execution took {duration:.2f}s, expected < 1.5s for 2 parallel 1s tasks"
