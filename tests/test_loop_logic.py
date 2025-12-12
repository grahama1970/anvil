
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import shutil

from src.anvil.orchestrator import run_debug_session, RunConfig
from src.anvil.artifacts.store import ArtifactStore
from src.anvil.providers.base import Provider, ProviderResult



import tempfile

class TestLoopLogic(unittest.TestCase):
    def setUp(self):
        self.tmp_dir_obj = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp_dir_obj.name)
        self.repo = self.tmp_dir / "repo"
        self.repo.mkdir()
    
    def tearDown(self):
        self.tmp_dir_obj.cleanup()
        
    def test_loop_runs_max_iters(self):
        # Setup tracks file
        tracks_file = self.tmp_dir / "tracks.yaml"
        tracks_file.write_text("""
tracks:
  - name: loop_test
    role: debugger
    provider: manual
    budgets:
      max_iters: 2
""")
        
        args = RunConfig(
            repo_path=self.repo,
            run_id="test_run",
            issue_text="fix",
            artifacts_root=self.tmp_dir / ".dbg",
            tracks_file=tracks_file,
            mode="debug",
        )
        
        # We need to inject MockLoopProvider.
        # orchestrator._provider_for_track calls generic loader.
        # We can patch it.
        
        with (
            patch("src.anvil.orchestrator.ContextBuilder") as MockCB,
            patch("src.anvil.orchestrator.ReproPlan") as MockRP,
            patch("src.anvil.orchestrator.WorktreeManager") as MockWT,
            patch("src.anvil.orchestrator._provider_for_track") as MockProviderLoader,
            # We assume TrackIterate works, but we can verify it creates files. 
            # Actually better to let TrackIterate run to assert side effects on fs?
            # But TrackIterate needs real redactor etc.
            # Let's mock TrackIterate.run to just create the ITERATION.json file so the loop logic (check signal) finds it!
            patch("src.anvil.orchestrator.TrackIterate") as MockTI_Cls, 
        ):
            # Create dummy artifacts
            run_dir = self.tmp_dir / ".dbg" / args.run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "CONTEXT.md").write_text("Dummy Context")
            (run_dir / "REPRO.md").write_text("Dummy Repro")

            # Configure mocks
            MockCB.return_value.check.return_value = 0
            MockRP.return_value.check.return_value = 0
            
            mock_ti = MockTI_Cls.return_value 
            # We need .check() to return 0
            mock_ti.check.return_value = 0
            
            # We need .run() to write a fake ITERATION.json so the loop logic can read "status_signal"
            # The loop logic looks at: store.path("tracks", t.name, f"iter_{iteration:02d}", "ITERATION.json")
            async def side_effect_run(*args, **kwargs):
                it = kwargs["iteration"]
                store = kwargs["store"]
                track = kwargs["track"]
                # Write file
                p = store.path("tracks", track, f"iter_{it:02d}", "ITERATION.json")
                p.parent.mkdir(parents=True, exist_ok=True)
                full_json = {
                    "schema_version": 1,
                    "track": track,
                    "iteration": it,
                    "status_signal": "CONTINUE",
                    "hypothesis": "test",
                    "confidence": 0.5,
                    "experiments": [],
                    "proposed_changes": {},
                    "risks": []
                }
                import json
                p.write_text(json.dumps(full_json))
                
            mock_ti.run.side_effect = side_effect_run
            
            # Execute
            result = asyncio.run(run_debug_session(args))
            
            # Check for crash
            crash = (self.tmp_dir / ".dbg" / args.run_id / "CRASH.txt")
            if crash.exists():
                print(f"CRASH LOG:\n{crash.read_text()}")
            
            status_f = (self.tmp_dir / ".dbg" / args.run_id / "RUN_STATUS.json")
            if status_f.exists():
                print(f"RUN_STATUS:\n{status_f.read_text()}")

            # Verify MockTI.run called twice
            self.assertEqual(mock_ti.run.call_count, 2)
            
            # Verify args
            calls = mock_ti.run.call_args_list
            self.assertEqual(calls[0].kwargs["iteration"], 1)
            self.assertEqual(calls[1].kwargs["iteration"], 2)

    def test_loop_stops_on_done(self):
        # Setup tracks file with max_iters 5
        tracks_file = self.tmp_dir / "tracks_done.yaml"
        tracks_file.write_text("""
tracks:
  - name: done_test
    role: debugger
    provider: manual
    budgets:
      max_iters: 5
""")
        args = RunConfig(
            repo_path=self.repo,
            run_id="test_run_done",
            issue_text="fix",
            artifacts_root=self.tmp_dir / ".dbg",
            tracks_file=tracks_file,
            mode="debug",
        )

        with (
            patch("src.anvil.orchestrator.ContextBuilder") as MockCB,
            patch("src.anvil.orchestrator.ReproPlan") as MockRP,
            patch("src.anvil.orchestrator._provider_for_track") as MockLoader,
            patch("src.anvil.orchestrator.TrackIterate") as MockTI_Cls, 
        ):
            # Create dummy artifacts
            run_dir = self.tmp_dir / ".dbg" / args.run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "CONTEXT.md").write_text("Dummy Context")
            (run_dir / "REPRO.md").write_text("Dummy Repro")

            MockCB.return_value.check.return_value = 0
            MockRP.return_value.check.return_value = 0
            mock_ti = MockTI_Cls.return_value 
            mock_ti.check.return_value = 0
            
            async def side_effect_run(iteration, store, track, **kwargs):
                p = store.path("tracks", track, f"iter_{iteration:02d}", "ITERATION.json")
                p.parent.mkdir(parents=True, exist_ok=True)
                # Iter 1: CONTINUE, Iter 2: DONE
                signal = "CONTINUE" if iteration < 2 else "DONE"
                full_json = {
                    "schema_version": 1,
                    "track": track,
                    "iteration": iteration,
                    "status_signal": signal,
                    "hypothesis": "test",
                    "confidence": 0.5,
                    "experiments": [],
                    "proposed_changes": {},
                    "risks": []
                }
                import json
                p.write_text(json.dumps(full_json))

            mock_ti.run.side_effect = side_effect_run

            asyncio.run(run_debug_session(args))
            
            # Verify called 2 times (stop after 2), even though max_iters=5
            self.assertEqual(mock_ti.run.call_count, 2)
