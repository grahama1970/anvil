from __future__ import annotations

"""Shell command execution.

CONTRACT
- Inputs: Command string, cwd, timeout
- Outputs (required):
  - CmdResult(returncode, stdout_path, stderr_path)
- Invariants:
  - Writes stdout/stderr to specified files
  - Respects timeout_s (raises SubprocessTimeout if exceeded)
- Failure:
  - Returns CmdResult with exit code (does NOT raise on non-zero exit)
"""

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
    elapsed_s: float
    stdout_bytes: int
    stderr_bytes: int


def run_cmd(
    cmd: str,
    cwd: Path,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    env: dict[str, str] | None = None,
    timeout_s: int | None = None,
) -> CmdResult:
    """Run a shell command and store stdout/stderr to files.

    CONTRACT:
    - Always writes stdout/stderr files (creates temp if not provided).
    - Never raises for non-zero exit; caller inspects return code.
    - Records duration and output size.
    """
    import time
    import tempfile
    
    # Handle optional paths by creating temp files if needed
    if stdout_path is None:
        tf_out = tempfile.NamedTemporaryFile(delete=False, prefix="dbg_stdout_")
        stdout_path = Path(tf_out.name)
        tf_out.close()
    if stderr_path is None:
        tf_err = tempfile.NamedTemporaryFile(delete=False, prefix="dbg_stderr_")
        stderr_path = Path(tf_err.name)
        tf_err.close()
    
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)

    start_t = time.time()
    with (
        stdout_path.open("w", encoding="utf-8") as out_f,
        stderr_path.open("w", encoding="utf-8") as err_f,
    ):
        try:
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
            rc = p.returncode
        except subprocess.TimeoutExpired:
            rc = 124  # Standard timeout exit code
            # We must output something to stderr?
            err_f.write("\nTimeout expired.\n")
        except Exception as e:
            rc = 1
            err_f.write(f"\nException: {e}\n")

    end_t = time.time()
    
    # Get byte counts
    out_b = stdout_path.stat().st_size if stdout_path.exists() else 0
    err_b = stderr_path.stat().st_size if stderr_path.exists() else 0

    return CmdResult(
        cmd=cmd,
        returncode=rc,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        elapsed_s=end_t - start_t,
        stdout_bytes=out_b,
        stderr_bytes=err_b,
    )


def run_cmd_docker(
    cmd: str,
    cwd: Path,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    env: dict[str, str] | None = None,
    timeout_s: int | None = None,
    image: str = "anvil:latest",
) -> CmdResult:
    """Run a command inside a Docker container with repository mounted.
    
    CONTRACT:
    - Wraps command in `docker run` with volume mounts
    - Mounts cwd to /repo in container
    - Ensures artifacts directory (.dbg) is accessible from host
    - Otherwise identical behavior to run_cmd()
    """
    # Construct docker run command
    # Mount the cwd as /repo in the container
    # Run the command in the mounted directory
    docker_cmd = [
        "docker", "run",
        "--rm",  # Clean up container after execution
        "-v", f"{cwd.absolute()}:/repo",  # Mount repo
        "-w", "/repo",  # Set working directory
    ]
    
    # Add environment variables if needed
    if env:
        for k, v in env.items():
            docker_cmd.extend(["-e", f"{k}={v}"])
    
    # Specify image and command
    docker_cmd.extend([
        image,
        "/bin/sh", "-c", cmd  # Execute command in shell
    ])
    
    # Convert to single command string
    full_cmd = " ".join(docker_cmd)
    
    # Use regular run_cmd to execute the docker command on the host
    return run_cmd(
        cmd=full_cmd,
        cwd=cwd,  # Host cwd (not used since docker sets -w)
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=None,  # Already passed to docker
        timeout_s=timeout_s,
    )


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Run shell commands safely")
    parser.add_argument("--cmd", required=True, help="Command to run")
    parser.add_argument("--cwd", default=".", help="Working directory")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout in seconds")
    args = parser.parse_args()

    stdout = Path("shell_cli.stdout.log")
    stderr = Path("shell_cli.stderr.log")

    try:
        res = run_cmd(
            cmd=args.cmd,
            cwd=Path(args.cwd),
            stdout_path=stdout,
            stderr_path=stderr,
            timeout_s=args.timeout,
        )
        print(f"Exit code: {res.returncode}")
        print(f"Stdout: {stdout.read_text(encoding='utf-8')}")
        print(f"Stderr: {stderr.read_text(encoding='utf-8')}")
        sys.exit(res.returncode)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
