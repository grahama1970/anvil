import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import anvil

class TestPublicAPI(unittest.TestCase):
    def test_debug_return_keys(self):
        """Ensure debug() returns keys promised in README."""
        
        # Mock result of run_debug_session
        mock_run_result = MagicMock()
        mock_run_result.status = "OK"
        mock_run_result.run_dir = Path("/tmp/run_dir")
        mock_run_result.decision_file = Path("/tmp/run_dir/DECISION.md")
        
        # Mock scorecard content for winner extraction
        def mock_read_text_side_effect():
            return '{"winner": "track_A"}'
        
        # We need to simulate the file system for SCORECARD.json
        with patch("anvil.orchestrator.run_debug_session", new_callable=AsyncMock) as mock_run, \
             patch("pathlib.Path.resolve", return_value=Path("/tmp/repo")), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", side_effect=mock_read_text_side_effect), \
             patch("pathlib.Path.glob", return_value=[]):
            
            mock_run.return_value = mock_run_result
            
            # Call API
            result = anvil.debug("/tmp/repo", "bug")
            
            # Assert Keys
            self.assertIn("status", result)
            self.assertIn("run_dir", result)
            self.assertIn("winner", result)     # Crucial for agents
            self.assertIn("patch_file", result) # Crucial for agents
            self.assertIn("patches", result)
            
            # Verify values
            self.assertEqual(result["winner"], "track_A")

    def test_harden_return_keys(self):
        """Ensure harden() returns keys promised in README."""
        
        mock_run_result = MagicMock()
        mock_run_result.status = "DONE"
        mock_run_result.run_dir = Path("/tmp/run_dir")
        
        with patch("anvil.orchestrator.run_harden_session", new_callable=AsyncMock) as mock_run, \
             patch("pathlib.Path.resolve", return_value=Path("/tmp/repo")), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="findings"), \
             patch("pathlib.Path.glob", return_value=[]):
             
            mock_run.return_value = mock_run_result
            
            result = anvil.harden("/tmp/repo")
            
            self.assertIn("status", result)
            self.assertIn("run_dir", result)
            self.assertIn("findings", result)
            self.assertIn("patches", result)
