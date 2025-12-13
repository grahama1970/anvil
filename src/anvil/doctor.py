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
import yaml

from .util.shell import which, run_cmd


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

    # 1. Critical: Git Repo
    if _is_git_repo(repo):
        items.append(DoctorItem("git repo", "OK", str(repo)))
    else:
        ok = False
        items.append(DoctorItem("git repo", "FAIL", "Not a git repo (required for worktrees)."))

    # 2. Critical: Verify Contract
    contract_path = repo / ".dbg" / "verify_contract.yaml"
    if contract_path.exists():
        try:
            data = yaml.safe_load(contract_path.read_text()) or {}
            cmds = data.get("commands", [])
            if cmds:
                items.append(DoctorItem("verify contract", "OK", f"{len(cmds)} commands found"))
            else:
                items.append(DoctorItem("verify contract", "WARN", "Contract exists but has NO commands (verification will be no-op PASS)"))
        except Exception as e:
            items.append(DoctorItem("verify contract", "WARN", f"Invalid YAML: {e}"))
    else:
        # Not strictly critical for Anvil logic, but critical for "No Vibes" guarantee
        items.append(DoctorItem("verify contract", "WARN", "Missing .dbg/verify_contract.yaml (verification will be no-op PASS)"))

    # 3. Binaries
    git_bin = which("git")
    if git_bin:
        items.append(DoctorItem("git binary", "OK", git_bin))
    else:
        ok = False
        items.append(DoctorItem("git binary", "FAIL", "git not found in PATH"))

    docker_bin = which("docker")
    if docker_bin:
        # Check docker connectivity
        res = run_cmd("docker info", cwd=repo, timeout_s=5)
        if res.returncode == 0:
            items.append(DoctorItem("docker", "OK", docker_bin))
        else:
            items.append(DoctorItem("docker", "WARN", "docker installed but not running/accessible"))
    else:
        items.append(DoctorItem("docker", "WARN", "docker not found; --docker mode unavailable"))

    rg_bin = which("rg")
    if rg_bin:
        items.append(DoctorItem("ripgrep", "OK", rg_bin))
    else:
        items.append(DoctorItem("ripgrep", "WARN", "rg not found; context search will degrade"))

    # 4. Providers & Auth
    gh_bin = which("gh")
    if gh_bin:
        # Check auth
        res = run_cmd("gh auth status", cwd=repo, timeout_s=5)
        status = "OK" if res.returncode == 0 else "WARN"
        details = "Auth valid" if res.returncode == 0 else "Not logged in (run `gh auth login`)"
        items.append(DoctorItem("gh cli", status, details))
    else:
        items.append(DoctorItem("gh cli", "INFO", "gh not found; gh_cli provider unavailable"))

    copilot_bin = which("copilot")
    if copilot_bin:
        # Check auth
        # copilot auth status might not be standard, usually copilot needs explicit setup
        # There isn't a simple "copilot auth status" command for the CLI wrapper usually, 
        # but we can try `copilot auth check` if it exists, or assume if binary exists.
        # Actually, for the github copilot CLI extension: `gh copilot --help` maybe?
        # If this is the standalone copilot-cli-agent, it uses tokens.
        # Let's just report binary presence for now to be safe.
        items.append(DoctorItem("copilot cli", "OK", copilot_bin))
    else:
        items.append(
            DoctorItem("copilot cli", "INFO", "copilot not found; copilot provider unavailable")
        )
    
    # Check for gh copilot extension if main copilot binary missing
    if gh_bin and not copilot_bin:
        res = run_cmd("gh extension list", cwd=repo, timeout_s=5)
        if res.returncode == 0 and "copilot" in res.stdout_content:
             items.append(DoctorItem("gh copilot", "OK", "Found gh-copilot extension"))

    gemini_bin = which("gemini")
    if gemini_bin:
        items.append(DoctorItem("gemini cli", "OK", gemini_bin))
    else:
        items.append(
            DoctorItem("gemini cli", "INFO", "gemini not found; gemini provider unavailable")
        )

    claude_bin = which("claude")
    if claude_bin:
        items.append(DoctorItem("claude cli", "OK", claude_bin))
    else:
        items.append(
            DoctorItem("claude cli", "INFO", "claude not found; claude provider unavailable")
        )

    return DoctorReport(ok=ok, items=items)
