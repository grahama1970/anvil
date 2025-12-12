import pytest
from typer.testing import CliRunner
from src.debugger.cli import app

runner = CliRunner()

def test_cli_help():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "Contract-driven debug" in res.stdout

def test_cli_version():
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "dbg version" in res.stdout

def test_init_help():
    res = runner.invoke(app, ["init", "--help"])
    assert res.exit_code == 0

def test_debug_run_help():
    res = runner.invoke(app, ["debug", "run", "--help"])
    assert res.exit_code == 0

def test_harden_run_help():
    res = runner.invoke(app, ["harden", "run", "--help"])
    assert res.exit_code == 0

def test_doctor_smoke():
    # Doctor might fail if dependencies are missing, but it should exit with code 0 or 2, not crash.
    # We just check it runs.
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code in [0, 2]
    assert "dbg doctor" in res.stdout
