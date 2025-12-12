from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


def which(cmd: str) -> str | None:
    for p in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(p) / cmd
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


@dataclass(frozen=True)
class CmdResult:
    cmd: str
    returncode: int
    stdout_path: Path
    stderr_path: Path


def run_cmd(
    cmd: str,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    env: dict[str, str] | None = None,
    timeout_s: int | None = None,
) -> CmdResult:
    """Run a shell command and store stdout/stderr to files.

    CONTRACT:
    - Always writes stdout/stderr files.
    - Never raises for non-zero exit; caller inspects return code.
    """
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)

    with (
        stdout_path.open("w", encoding="utf-8") as out_f,
        stderr_path.open("w", encoding="utf-8") as err_f,
    ):
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            shell=True,
            env=(os.environ | env) if env else None,
            stdout=out_f,
            stderr=err_f,
            timeout=timeout_s,
            text=True,
        )
    return CmdResult(
        cmd=cmd, returncode=p.returncode, stdout_path=stdout_path, stderr_path=stderr_path
    )
