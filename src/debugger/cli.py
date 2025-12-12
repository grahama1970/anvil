"""CLI entrypoint.

Two primary modes:
- dbg debug ...
- dbg harden ...

Utilities:
- dbg init
- dbg doctor
"""

from __future__ import annotations

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
) -> None:
    """Write `.dbg/` templates into a target repo."""
    from .init import write_templates

    write_templates(repo)
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
    result = run_debug_session(cfg)
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
    result = run_debug_session(cfg)
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
    )
    result = run_harden_session(cfg)
    console.print(f"[bold]Harden[/bold] {rid} finished with status: {result.status}")
    console.print(f"Artifacts: {result.run_dir}")


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
