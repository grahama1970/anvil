"""CLI entrypoint.

Two primary modes:
- dbg debug ...
- dbg harden ...

Utilities:
- dbg init
- dbg doctor

CONTRACT
- Inputs: Command line arguments (parsed by Typer)
- Outputs (required):
  - Exit code 0 on success, non-zero on failure
  - Console output (stdout/stderr) describing progress/results
- Invariants:
  - All commands validate their inputs (run_id, track_name) before execution
  - Orchestrator actions are delegated to appropriate modules
- Failure:
  - Invalid arguments raise Typer exit/error
  - Runtime errors are caught and printed by Typer or the orchestrator
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import RunConfig
from .doctor import doctor_report
from .orchestrator import run_debug_session, run_harden_session
from .util.ids import new_run_id, validate_run_id, validate_track_name
from .util.paths import ensure_dir
from .util.text import read_text_file

app = typer.Typer(add_completion=False, help="Contract-driven debug + harden harness (no vibes).")
debug_app = typer.Typer(add_completion=False, help="Debug an issue-like prompt.")
harden_app = typer.Typer(add_completion=False, help="Red-team/harden a repo or candidate patch.")
app.add_typer(debug_app, name="debug")
app.add_typer(harden_app, name="harden")

def _version_callback(value: bool):
    if value:
        # Import dynamically to avoid circular deps if any
        # Assuming version is stored in package init or accessible
        # For now, hardcode or read from pyproject.toml in real app.
        try:
            from .. import __version__
        except ImportError:
            __version__ = "0.1.0"
        console.print(f"dbg version: {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version."
    )
):
    pass

console = Console()

_REPO_OPTION = typer.Option(
    Path("."),
    "--repo",
    help="Target repo root (default: current dir).",
)
_REPO_OPTION_PLAIN = typer.Option(
    Path("."),
    "--repo",
    help="Target repo root.",
)
_REPO_OPTION_GIT = typer.Option(
    Path("."),
    "--repo",
    help="Target git repo root.",
)
_ARTIFACTS_DIR_OPTION = typer.Option(
    Path(".dbg/runs"),
    "--artifacts-dir",
    help="Artifacts root dir.",
)
_ARTIFACTS_DIR_OPTION_ROOT = typer.Option(
    Path(".dbg/runs"),
    "--artifacts-dir",
    help="Artifacts root.",
)
_RUN_ID_OPTION = typer.Option(
    None,
    "--run-id",
    help="Run id (default: auto).",
)
_RUN_ID_REQUIRED_OPTION = typer.Option(
    ...,
    "--run",
    help="Run id.",
)
_TRACKS_FILE_OPTION = typer.Option(
    None,
    "--tracks-file",
    help="Tracks YAML file.",
)
_TRACKS_FILE_OPTIONAL_OPTION = typer.Option(
    None,
    "--tracks-file",
    help="Tracks YAML file (optional).",
)
_ISSUE_FILE_OPTION = typer.Option(
    None,
    "--issue-file",
    help="Issue markdown file.",
)
_ISSUE_OPTION = typer.Option(
    None,
    "--issue",
    help="Issue text (GitHub-issue-like).",
)
_VERBOSE_OPTION = typer.Option(
    False,
    "--verbose",
    help="Show more details.",
)
_DOCKER_OPTION = typer.Option(
    False,
    "--docker",
    help="Run steps inside docker (best effort).",
)
_TREESITTER_OPTION = typer.Option(
    False,
    "--use-treesitter",
    help="Enable optional tree-sitter outline.",
)
_CANDIDATE_RUN_OPTION = typer.Option(
    None,
    "--candidate-run",
    help="Use a previous debug run's artifacts.",
)
_CANDIDATE_TRACK_OPTION = typer.Option(
    None,
    "--candidate-track",
    help="Track name from candidate run.",
)


@app.command()
def init(
    repo: Path = _REPO_OPTION,
    force: bool = typer.Option(False, "--force", help="Overwrite existing templates."),
) -> None:
    """Write `.dbg/` templates into a target repo."""
    from .init import write_templates

    write_templates(repo, force=force)
    console.print(f"[green]Wrote templates to[/green] {repo / '.dbg'}")


@app.command()
def doctor(
    repo: Path = _REPO_OPTION_PLAIN,
    verbose: bool = _VERBOSE_OPTION,
) -> None:
    """Environment and preflight checks."""
    report = doctor_report(repo=repo, verbose=verbose)
    table = Table(title="dbg doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")
    for item in report.items:
        table.add_row(item.name, item.status, item.details)
    console.print(table)
    if report.ok:
        console.print("[green]OK[/green]")
    else:
        raise typer.Exit(code=2)


@debug_app.command("run")
def debug_run(
    repo: Path = _REPO_OPTION_GIT,
    issue_file: Path | None = _ISSUE_FILE_OPTION,
    issue: str | None = _ISSUE_OPTION,
    tracks_file: Path | None = _TRACKS_FILE_OPTION,
    artifacts_dir: Path = _ARTIFACTS_DIR_OPTION,
    run_id: str | None = _RUN_ID_OPTION,
    use_docker: bool = _DOCKER_OPTION,
    use_treesitter: bool = _TREESITTER_OPTION,
) -> None:
    """Run the full debug workflow."""
    issue_text = None
    if issue_file:
        if not issue_file.exists():
            raise typer.BadParameter(f"Issue file not found: {issue_file}")
        issue_text = read_text_file(issue_file)
    elif issue:
        issue_text = issue
    else:
        raise typer.BadParameter("Provide --issue-file or --issue.")

    rid = validate_run_id(run_id or new_run_id())
    ensure_dir(artifacts_dir)

    cfg = RunConfig(
        repo_path=repo,
        run_id=rid,
        artifacts_root=artifacts_dir,
        tracks_file=tracks_file,
        issue_text=issue_text,
        mode="debug",
        use_docker=use_docker,
        use_treesitter=use_treesitter,
    )
    result = asyncio.run(run_debug_session(cfg))
    console.print(f"[bold]Run[/bold] {rid} finished with status: {result.status}")
    console.print(f"Artifacts: {result.run_dir}")
    if result.decision_file:
        console.print(f"Decision: {result.decision_file}")


@debug_app.command("status")
def debug_status(
    repo: Path = _REPO_OPTION_PLAIN,
    run_id: str = _RUN_ID_REQUIRED_OPTION,
    artifacts_dir: Path = _ARTIFACTS_DIR_OPTION_ROOT,
) -> None:
    validate_run_id(run_id)
    run_dir = artifacts_dir / run_id
    status_path = run_dir / "RUN_STATUS.json"
    if not status_path.exists():
        raise typer.BadParameter(f"No status found: {status_path}")
    console.print_json(status_path.read_text(encoding="utf-8"))


@debug_app.command("resume")
def debug_resume(
    repo: Path = _REPO_OPTION_PLAIN,
    run_id: str = _RUN_ID_REQUIRED_OPTION,
    artifacts_dir: Path = _ARTIFACTS_DIR_OPTION_ROOT,
) -> None:
    validate_run_id(run_id)
    cfg = RunConfig(
        repo_path=repo,
        run_id=run_id,
        artifacts_root=artifacts_dir,
        tracks_file=None,
        issue_text=None,
        mode="debug",
        resume=True,
    )
    result = asyncio.run(run_debug_session(cfg))
    console.print(f"[bold]Run[/bold] {run_id} resumed, status: {result.status}")
    console.print(f"Artifacts: {result.run_dir}")


@harden_app.command("run")
def harden_run(
    repo: Path = _REPO_OPTION_PLAIN,
    tracks_file: Path | None = _TRACKS_FILE_OPTIONAL_OPTION,
    artifacts_dir: Path = _ARTIFACTS_DIR_OPTION,
    run_id: str | None = _RUN_ID_OPTION,
    candidate_run: str | None = _CANDIDATE_RUN_OPTION,
    candidate_track: str | None = _CANDIDATE_TRACK_OPTION,
    use_docker: bool = _DOCKER_OPTION,
    verify_patches: bool = typer.Option(False, "--verify-patches", help="Run per-iteration verification."),
) -> None:
    rid = validate_run_id(run_id or new_run_id())
    ensure_dir(artifacts_dir)
    if candidate_run is not None:
        validate_run_id(candidate_run)
    if candidate_track is not None:
        validate_track_name(candidate_track)
    cfg = RunConfig(
        repo_path=repo,
        run_id=rid,
        artifacts_root=artifacts_dir,
        tracks_file=tracks_file,
        issue_text=None,
        mode="harden",
        use_docker=use_docker,
        candidate_run=candidate_run,
        candidate_track=candidate_track,
        verify_patches=verify_patches,
    )
    result = asyncio.run(run_harden_session(cfg))
    console.print(f"[bold]Harden[/bold] {rid} finished with status: {result.status}")
    console.print(f"Artifacts: {result.run_dir}")
    if result.decision_file:
        console.print(f"Report: {result.decision_file}")


@harden_app.command("status")
def harden_status(
    run_id: str = _RUN_ID_REQUIRED_OPTION,
    artifacts_dir: Path = _ARTIFACTS_DIR_OPTION_ROOT,
) -> None:
    validate_run_id(run_id)
    run_dir = artifacts_dir / run_id
    status_path = run_dir / "RUN_STATUS.json"
    if not status_path.exists():
        raise typer.BadParameter(f"No status found: {status_path}")
    console.print_json(status_path.read_text(encoding="utf-8"))


# Cleanup CLI
cleanup_app = typer.Typer(add_completion=False, help="Manage and cleanup worktrees.")
app.add_typer(cleanup_app, name="cleanup")


@cleanup_app.command("run")
def cleanup_run(
    repo: Path = _REPO_OPTION_PLAIN,
    run_id: str = _RUN_ID_REQUIRED_OPTION,
    artifacts_dir: Path = _ARTIFACTS_DIR_OPTION_ROOT,
) -> None:
    """Clean up worktrees for a specific run."""
    from .worktrees import WorktreeManager
    from .artifacts.store import ArtifactStore
    
    validate_run_id(run_id)
    store = ArtifactStore(artifacts_dir / run_id)
    wt = WorktreeManager(repo, store)
    
    # Identify tracks from worktree directory structure
    # We can't trust tracks.yaml or RUN.json to exist if run crashed early, 
    # so we look at actual directories on disk.
    wt_root = wt._worktrees_root()
    if not wt_root.exists():
        console.print(f"[yellow]No worktrees found for run {run_id}[/yellow]")
        return
        
    tracks = [
        d.name for d in wt_root.iterdir() 
        if d.is_dir() and (d / ".git").exists()
    ]
    
    if not tracks:
         # Maybe directories exist but not valid worktrees?
         # Just listing dirs is safer to attempt cleanup on everything
         tracks = [d.name for d in wt_root.iterdir() if d.is_dir()]

    if not tracks:
        console.print(f"[yellow]No worktree directories found for run {run_id}[/yellow]")
        return

    console.print(f"Cleaning worktrees for run {run_id}: {tracks}")
    wt.cleanup(tracks)
    console.print("[green]Done[/green]")


@cleanup_app.command("all")
def cleanup_all(
    repo: Path = _REPO_OPTION_PLAIN,
    artifacts_dir: Path = _ARTIFACTS_DIR_OPTION_ROOT,
) -> None:
    """Clean ALL anvil worktrees (destructive)."""
    from .worktrees import WorktreeManager
    from .artifacts.store import ArtifactStore
    
    # Dummy store to init manager
    store = ArtifactStore(artifacts_dir / "dummy")
    wt = WorktreeManager(repo, store)
    
    root = wt._all_worktrees_root()
    if not root.exists():
        console.print("No worktrees root found.")
        return
        
    runs = [d.name for d in root.iterdir() if d.is_dir()]
    if not runs:
        console.print("No runs found in worktrees.")
        return
        
    if not typer.confirm(f"This will remove worktrees for {len(runs)} runs. Are you sure?"):
        raise typer.Abort()
        
    count = 0
    for run_id in runs:
        # Re-init manager for specific run to get correct paths/branches
        r_store = ArtifactStore(artifacts_dir / run_id)
        r_wt = WorktreeManager(repo, r_store)
        
        r_root = r_wt._worktrees_root()
        if r_root.exists():
            tracks = [d.name for d in r_root.iterdir() if d.is_dir()]
            if tracks:
                r_wt.cleanup(tracks)
                count += 1
                
    console.print(f"[green]Cleaned worktrees for {count} runs.[/green]")


@cleanup_app.command("stale")
def cleanup_stale(
    repo: Path = _REPO_OPTION_PLAIN,
    artifacts_dir: Path = _ARTIFACTS_DIR_OPTION_ROOT,
    older_than: int = typer.Option(7, "--older-than", help="Days threshold"),
) -> None:
    """Clean stale worktrees older than N days."""
    from .worktrees import WorktreeManager
    from .artifacts.store import ArtifactStore
    
    store = ArtifactStore(artifacts_dir / "dummy")
    wt = WorktreeManager(repo, store)
    
    count = wt.cleanup_stale_worktrees(older_than_days=older_than)
    if count > 0:
        console.print(f"[green]Removed {count} stale worktrees/tracks[/green]")
    else:
        console.print("No stale worktrees found.")


@cleanup_app.command("list")
def cleanup_list(
    repo: Path = _REPO_OPTION_PLAIN,
    artifacts_dir: Path = _ARTIFACTS_DIR_OPTION_ROOT,
) -> None:
    """List all anvil worktrees."""
    from .worktrees import WorktreeManager
    from .artifacts.store import ArtifactStore
    
    store = ArtifactStore(artifacts_dir / "dummy")
    wt = WorktreeManager(repo, store)
    
    root = wt._all_worktrees_root()
    if not root.exists():
        console.print("No worktrees found.")
        return
        
    table = Table(title="Anvil Worktrees")
    table.add_column("Run ID")
    table.add_column("Track")
    table.add_column("Path")
    
    found_any = False
    for run_dir in root.iterdir():
        if not run_dir.is_dir():
             continue
        run_id = run_dir.name
        for t_dir in run_dir.iterdir():
            if t_dir.is_dir():
                table.add_row(run_id, t_dir.name, str(t_dir))
                found_any = True
                
    if found_any:
        console.print(table)
    else:
        console.print("No worktrees found.")


if __name__ == "__main__":
    app()
