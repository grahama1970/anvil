from __future__ import annotations

"""Environment health checks.

CONTRACT
- Inputs: Repo path
- Outputs (required):
  - DoctorReport (ok=bool, items=[(name, status, details)])
- Invariants:
  - Checks: git repo, git binary, docker, ripgrep, gh cli, copilot cli, gemini cli
  - Does not modify system state (read-only checks)
- Failure:
  - Returns DoctorReport with ok=False if critical checks fail (git repo, git binary)
"""

from dataclasses import dataclass
from pathlib import Path

from .util.shell import which


@dataclass(frozen=True)
class DoctorItem:
    name: str
    status: str
    details: str


@dataclass(frozen=True)
class DoctorReport:
    ok: bool
    items: list[DoctorItem]


def _is_git_repo(repo: Path) -> bool:
    return (repo / ".git").exists() or (repo / ".git").is_file()


def doctor_report(repo: Path, verbose: bool = False) -> DoctorReport:
    items: list[DoctorItem] = []
    ok = True

    if _is_git_repo(repo):
        items.append(DoctorItem("git repo", "OK", str(repo)))
    else:
        ok = False
        items.append(DoctorItem("git repo", "FAIL", "Not a git repo (required for worktrees)."))

    git_bin = which("git")
    if git_bin:
        items.append(DoctorItem("git binary", "OK", git_bin))
    else:
        ok = False
        items.append(DoctorItem("git binary", "FAIL", "git not found in PATH"))

    docker_bin = which("docker")
    if docker_bin:
        items.append(DoctorItem("docker", "OK", docker_bin))
    else:
        items.append(DoctorItem("docker", "WARN", "docker not found; --docker mode unavailable"))

    rg_bin = which("rg")
    if rg_bin:
        items.append(DoctorItem("ripgrep", "OK", rg_bin))
    else:
        items.append(DoctorItem("ripgrep", "WARN", "rg not found; context search will degrade"))

    gh_bin = which("gh")
    if gh_bin:
        items.append(DoctorItem("gh cli", "OK", gh_bin))
    else:
        items.append(DoctorItem("gh cli", "INFO", "gh not found; gh_cli provider unavailable"))

    copilot_bin = which("copilot")
    if copilot_bin:
        items.append(DoctorItem("copilot cli", "OK", copilot_bin))
    else:
        items.append(
            DoctorItem("copilot cli", "INFO", "copilot not found; copilot provider unavailable")
        )

    gemini_bin = which("gemini")
    if gemini_bin:
        items.append(DoctorItem("gemini cli", "OK", gemini_bin))
    else:
        items.append(
            DoctorItem("gemini cli", "INFO", "gemini not found; gemini provider unavailable")
        )

    return DoctorReport(ok=ok, items=items)
