import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.anvil.util.shell import run_cmd, run_cmd_docker, CmdResult

def test_run_cmd_list_mode(tmp_path):
    """Test that run_cmd with a list arg uses shell=False."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        cmd = ["ls", "-l"]
        run_cmd(cmd, tmp_path)
        
        # Verify shell=False was used
        args, kwargs = mock_run.call_args
        assert args[0] == cmd
        assert kwargs["shell"] is False
        assert kwargs["cwd"] == str(tmp_path)

def test_run_cmd_docker_construction(tmp_path):
    """Test that run_cmd_docker constructs correct docker args."""
    with patch("src.anvil.util.shell.run_cmd") as mock_run_cmd:
        mock_run_cmd.return_value = CmdResult(
            cmd="", returncode=0, stdout_path=Path(""), stderr_path=Path(""),
            elapsed_s=0, stdout_bytes=0, stderr_bytes=0
        )
        
        user_cmd = "echo 'hello world'"
        cwd = tmp_path.resolve()
        
        run_cmd_docker(user_cmd, cwd, env={"TEST_VAR": "val"})
        
        # Check what was passed to run_cmd
        args, kwargs = mock_run_cmd.call_args
        passed_cmd = kwargs["cmd"]
        
        # It should be a list
        assert isinstance(passed_cmd, list)
        
        # Structure should be:
        # docker run --rm -v resolved_cwd:/repo -w /repo -e TEST_VAR=val anvil:latest /bin/sh -c cmd
        assert passed_cmd[0] == "docker"
        assert passed_cmd[1] == "run"
        assert "--rm" in passed_cmd
        
        # Check volume mount
        expected_mount = f"{cwd}:/repo"
        assert "-v" in passed_cmd
        mount_idx = passed_cmd.index("-v") + 1
        assert passed_cmd[mount_idx] == expected_mount
        
        # Check env
        assert "-e" in passed_cmd
        env_idx = passed_cmd.index("-e") + 1
        assert passed_cmd[env_idx] == "TEST_VAR=val"
        
        # Check image and command
        assert "anvil:latest" in passed_cmd
        assert "/bin/sh" in passed_cmd
        assert "-c" in passed_cmd
        assert passed_cmd[-1] == user_cmd
