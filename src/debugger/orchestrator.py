from __future__ import annotations

import traceback
from dataclasses import dataclass
from dataclasses import fields as dataclass_fields
from pathlib import Path

from .artifacts.schemas import RunMeta, RunStatus
from .artifacts.store import ArtifactStore
from .collab.blackboard import Blackboard
from .config import RunConfig, TrackConfig, load_tracks_file
from .providers.base import Provider, ProviderResult
from .providers.copilot_cli import CopilotCliProvider
from .providers.gemini_cli import GeminiCliProvider
from .providers.gh_cli import GhCliProvider
from .providers.manual import ManualProvider
from .score.compute import ScoreComputer
from .steps.apply import Apply
from .steps.context_builder import ContextBuilder
from .steps.judge import Judge
from .steps.repro_plan import ReproPlan
from .steps.track_iterate import TrackIterate
from .steps.verify import Verify
from .util.events import EventLog
from .worktrees import WorktreeManager


@dataclass(frozen=True)
class RunResult:
    status: str
    run_dir: Path
    decision_file: Path | None = None


def _default_tracks() -> list[TrackConfig]:
    # Fallback if no tracks file is provided.
    from .config import TrackBudget

    return [
        TrackConfig(
            name="A",
            role="backend_fixer",
            provider="manual",
            directions_profile="strict_minimal_patch",
            budgets=TrackBudget(),
        ),
        TrackConfig(
            name="B",
            role="explorer",
            provider="manual",
            directions_profile="creative_unblock_then_minimize",
            budgets=TrackBudget(),
        ),
    ]


def _filter_provider_kwargs(cls: type, opts: dict[str, object]) -> dict[str, object]:
    allowed = {f.name for f in dataclass_fields(cls)}
    return {k: v for k, v in opts.items() if k in allowed}


def _provider_for_track(t: TrackConfig) -> Provider:
    if t.provider == "manual":
        return ManualProvider()
    if t.provider == "copilot":
        opts = _filter_provider_kwargs(CopilotCliProvider, t.provider_options)
        opts["model"] = t.model or "gpt-5"
        return CopilotCliProvider(**opts)
    if t.provider == "gemini":
        opts = _filter_provider_kwargs(GeminiCliProvider, t.provider_options)
        opts["model"] = t.model or "gemini-3-pro"
        return GeminiCliProvider(**opts)
    if t.provider == "gh_cli":
        return GhCliProvider()
    raise ValueError(f"Unknown provider: {t.provider}")


@dataclass
class _ErrorProvider(Provider):
    error: str

    def run_iteration(
        self,
        *,
        repo: Path,
        track: str,
        iteration: int,
        role: str,
        directions: str,
        context: str,
        blackboard: str,
    ) -> ProviderResult:
        raise RuntimeError(self.error)


def _load_tracks(cfg: RunConfig) -> tuple[list[TrackConfig], bool, int]:
    if cfg.tracks_file and cfg.tracks_file.exists():
        tf = load_tracks_file(cfg.tracks_file)
        use_ts = cfg.use_treesitter or tf.context.use_treesitter
        max_files = tf.context.max_files
        return tf.tracks, use_ts, max_files
    # try repo .dbg/tracks.yaml
    repo_tracks = cfg.repo_path / ".dbg" / "tracks.yaml"
    if repo_tracks.exists():
        tf = load_tracks_file(repo_tracks)
        use_ts = cfg.use_treesitter or tf.context.use_treesitter
        max_files = tf.context.max_files
        return tf.tracks, use_ts, max_files
    return _default_tracks(), cfg.use_treesitter, 25


def run_debug_session(cfg: RunConfig) -> RunResult:
    store = ArtifactStore(cfg.run_dir())
    store.ensure()
    ev = EventLog(store.path("events.jsonl"))

    try:
        tracks, use_ts, max_files = _load_tracks(cfg)
        wt = WorktreeManager(repo=cfg.repo_path, store=store)

        meta = RunMeta(
            run_id=cfg.run_id,
            repo_path=str(cfg.repo_path),
            mode=cfg.mode,
            issue_text_present=bool(cfg.issue_text),
            use_docker=cfg.use_docker,
            use_treesitter=use_ts,
            tracks=[t.__dict__ for t in tracks],
        )
        store.write_run_meta(meta)

        status = RunStatus(run_id=cfg.run_id, mode=cfg.mode, status="RUNNING", message="starting")
        store.write_status(status)

        # Setup worktrees (best effort)
        ev.emit(stage="setup", action="worktrees_create")
        wt.create_worktrees([t.name for t in tracks])

        # Per-worktree contracts
        wt.write_worktree_contracts(tracks)

        # Steps
        issue_text = cfg.issue_text or ""
        ContextBuilder().run(
            store, cfg.repo_path, issue_text=issue_text, use_treesitter=use_ts, max_files=max_files
        )
        if ContextBuilder().check(store, cfg.repo_path) != 0:
            store.write_status(
                RunStatus(
                    run_id=cfg.run_id, mode=cfg.mode, status="FAIL", message="context check failed"
                )
            )
            return RunResult(status="FAIL", run_dir=store.run_dir)

        ReproPlan().run(store, cfg.repo_path, issue_text=issue_text)
        if ReproPlan().check(store, cfg.repo_path) != 0:
            store.write_status(
                RunStatus(
                    run_id=cfg.run_id, mode=cfg.mode, status="FAIL", message="repro check failed"
                )
            )
            return RunResult(status="FAIL", run_dir=store.run_dir)

        context_text = store.path("CONTEXT.md").read_text(encoding="utf-8", errors="ignore")
        blackboard_text = ""

        disqualified: list[str] = []

        # Iterate each track (one iteration default; extend via agent loops later)
        for t in tracks:
            try:
                provider = _provider_for_track(t)
            except Exception as exc:
                provider = _ErrorProvider(error=f"Provider init failed for {t.provider}: {exc}")
            iter_step = TrackIterate()
            iteration = 1
            ev.emit(
                stage="iterate",
                track=t.name,
                iter=iteration,
                action="provider_call",
                provider=t.provider,
                model=t.model or "",
            )
            iter_step.run(
                store=store,
                repo=cfg.repo_path,
                track=t.name,
                role=t.role,
                provider=provider,
                iteration=iteration,
                directions_profile=t.directions_profile,
                context_text=context_text,
                blackboard_text=blackboard_text,
            )
            chk = iter_step.check(store, cfg.repo_path, track=t.name, iteration=iteration)
            if chk != 0:
                disqualified.append(t.name)
                ev.emit(
                    stage="iterate",
                    track=t.name,
                    iter=iteration,
                    action="disqualified",
                    reason="iterate_check_failed",
                )

        # Build blackboard (observations-only)
        Blackboard().write(store, [t.name for t in tracks])
        blackboard_text = store.path("BLACKBOARD.md").read_text(encoding="utf-8", errors="ignore")

        # Verify (optional but part of workflow)
        ev.emit(stage="verify", action="run")
        Verify().run(store, cfg.repo_path)
        Verify().check(store, cfg.repo_path)

        # Score (artifact-backed)
        ScoreComputer().write(store, [t.name for t in tracks])

        # Judge
        ev.emit(stage="judge", action="run")
        decision = Judge().run(store, [t.name for t in tracks], disqualified=disqualified)
        Judge().check(store, cfg.repo_path)

        # Apply (only if we have a patch)
        winner = decision.winner
        applied = False
        if winner:
            patches = sorted(store.path("tracks", winner).glob("iter_*/PATCH.diff"))
            if patches:
                patch = patches[-1]
                ev.emit(stage="apply", action="run", winner=winner, patch=str(patch))
                rc = Apply().run(store, cfg.repo_path, patch_path=patch)
                applied = rc == 0

        final_status = "OK" if winner and applied else "DONE"
        store.write_status(
            RunStatus(
                run_id=cfg.run_id,
                mode=cfg.mode,
                status=final_status,
                message="completed",
                disqualified_tracks=disqualified,
            )
        )
        return RunResult(
            status=final_status,
            run_dir=store.run_dir,
            decision_file=store.path("DECISION.md") if store.path("DECISION.md").exists() else None,
        )
    except Exception as exc:  # pragma: no cover
        ev.emit(stage="crash", action="exception", error=str(exc))
        store.write_text("CRASH.txt", traceback.format_exc())
        store.write_status(
            RunStatus(run_id=cfg.run_id, mode=cfg.mode, status="FAIL", message=f"crash: {exc}")
        )
        return RunResult(status="FAIL", run_dir=store.run_dir)


def run_harden_session(cfg: RunConfig) -> RunResult:
    store = ArtifactStore(cfg.run_dir())
    store.ensure()
    ev = EventLog(store.path("events.jsonl"))

    try:
        meta = RunMeta(
            run_id=cfg.run_id,
            repo_path=str(cfg.repo_path),
            mode=cfg.mode,
            issue_text_present=False,
            use_docker=cfg.use_docker,
            use_treesitter=False,
            tracks=[],
        )
        store.write_run_meta(meta)
        store.write_status(
            RunStatus(run_id=cfg.run_id, mode=cfg.mode, status="RUNNING", message="starting harden")
        )

        # Minimal harden: run verify contract (same as debug) and produce HARDEN.md summary
        ev.emit(stage="harden", action="verify_run")
        Verify().run(store, cfg.repo_path)
        Verify().check(store, cfg.repo_path)

        verify_md = (
            store.path("VERIFY.md").read_text(encoding="utf-8", errors="ignore")
            if store.path("VERIFY.md").exists()
            else ""
        )
        harden_md = [
            "# HARDEN",
            "",
            "This is a minimal harden run. Extend with Breaker tracks and additional checks.",
            "",
            "## Verification results",
            "",
            verify_md,
            "",
        ]
        store.write_text("HARDEN.md", "\n".join(harden_md))

        store.write_status(
            RunStatus(run_id=cfg.run_id, mode=cfg.mode, status="DONE", message="harden completed")
        )
        return RunResult(status="DONE", run_dir=store.run_dir)
    except Exception as exc:  # pragma: no cover
        ev.emit(stage="crash", action="exception", error=str(exc))
        store.write_text("CRASH.txt", traceback.format_exc())
        store.write_status(
            RunStatus(run_id=cfg.run_id, mode=cfg.mode, status="FAIL", message=f"crash: {exc}")
        )
        return RunResult(status="FAIL", run_dir=store.run_dir)
