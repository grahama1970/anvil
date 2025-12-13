import asyncio
import unittest
import tempfile
from pathlib import Path
from anvil.orchestrator import run_debug_session, RunConfig

class TestValidationFailures(unittest.TestCase):
    def setUp(self):
        self.tmp_dir_obj = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp_dir_obj.name)
        # Do NOT init git repo - this triggers the failure
    
    def tearDown(self):
        self.tmp_dir_obj.cleanup()

    def test_fails_on_non_git_repo(self):
        """Ensure session fails hard if target is not a git repo."""
        args = RunConfig(
            repo_path=self.tmp_dir, # Non-git dir
            run_id="fail_test",
            issue_text="fix",
            artifacts_root=self.tmp_dir / ".dbg",
            tracks_file=None,
            mode="debug",
        )
        
        # Run without mocking WorktreeManager checks (so they fail)
        # But we need to mock internal components that might crash before validation?
        # No, validation happens early.
        # But we need to verify dependent components don't crash.
        # TrackIterate, etc, shouldn't be called if validation fails.
        
        # We assume run_debug_session handles the exception/return.
        result = asyncio.run(run_debug_session(args))
        
        self.assertEqual(result.status, "FAIL")
        
        # Check for diagnostics in log or error file
        # We can't easily check loguru output here without a sink, but we can check if CRASH.txt exists?
        # Actually validation failure writes WORKTREE_VALIDATION_ERROR.txt locally? 
        # No, it logs an error and returns FAIL. 
        # But `run_debug_session` writes `WORKTREE_VALIDATION_ERROR.txt` if validation fails (I implemented this).
        
        error_file = self.tmp_dir / ".dbg" / "fail_test" / "WORKTREE_VALIDATION_ERROR.txt"
        self.assertTrue(error_file.exists(), "WORKTREE_VALIDATION_ERROR.txt should be created")
        content = error_file.read_text()
        self.assertIn("Root cause: Repo is not a git repository", content)
