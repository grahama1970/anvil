import pytest
import sys
import os
from pathlib import Path
from anvil.util.shell import run_cmd, CmdResult

def test_run_cmd_success(tmp_path):
    stdout = tmp_path / "out.log"
    stderr = tmp_path / "err.log"
    
    cmd = "echo 'hello'" if sys.platform != "win32" else "echo hello"
    res = run_cmd(cmd, tmp_path, stdout, stderr)
    
    assert res.returncode == 0
    assert "hello" in stdout.read_text()
    assert res.stdout_bytes > 0
    assert res.elapsed_s >= 0

def test_run_cmd_failure(tmp_path):
    stdout = tmp_path / "out.log"
    stderr = tmp_path / "err.log"
    
    # False command
    cmd = "false" if sys.platform != "win32" else "exit 1"
    res = run_cmd(cmd, tmp_path, stdout, stderr)
    
    assert res.returncode != 0
    # Should not raise exception
    
def test_run_cmd_timeout(tmp_path):
    stdout = tmp_path / "out.log"
    stderr = tmp_path / "err.log"
    
    # Sleep 2s, timeout 0.5s
    cmd = "sleep 2" if sys.platform != "win32" else "timeout 2"
    
    # run_cmd catches TimeoutExpired and returns rc=124
    res = run_cmd(cmd, tmp_path, stdout, stderr, timeout_s=0.5)
    
    assert res.returncode == 124
    assert "Timeout expired" in stderr.read_text()

def test_run_cmd_capture(tmp_path):
    stdout = tmp_path / "out.log"
    stderr = tmp_path / "err.log"
    
    # Redirect stderr
    cmd = "echo 'error message' >&2" if sys.platform != "win32" else "echo error message 1>&2"
    res = run_cmd(cmd, tmp_path, stdout, stderr)
    
    assert res.returncode == 0
    content = stderr.read_text().strip()
    assert "error message" in content
    assert res.stderr_bytes > 0
