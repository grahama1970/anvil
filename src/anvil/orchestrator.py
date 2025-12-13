from __future__ import annotations

"""Orchestrator for debug and harden sessions.

CONTRACT
- Inputs: RunConfig (paths, mode, tracks, etc.)
- Outputs (required):
  - RunResult (status, run_dir)
  - Artifacts in .dbg/runs/<run_id>/
    - RUN.json, RUN_STATUS.json
    - Step-specific artifacts (CONTEXT.md, REPRO.md, etc.)
- Invariants:
  - Always writes RUN.json and RUN_STATUS.json
  - Catches top-level exceptions, writes CRASH.txt, and reports FAIL status
  - Disqualifies tracks that fail checks
- Failure:
  - Returns RunResult(status="FAIL") on crash or critical step failure
"""

import asyncio
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
from .providers.claude_cli import ClaudeCliProvider
from .providers.manual import ManualProvider
from .score.compute import ScoreComputer
from .steps.apply import Apply
from .steps.context_builder import ContextBuilder
from .steps.judge import Judge
from .steps.repro_assess import ReproAssess
from .util.shell import run_cmd
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
    if t.provider == "claude":
        opts = _filter_provider_kwargs(ClaudeCliProvider, t.provider_options)
        return ClaudeCliProvider(**opts)
    raise ValueError(f"Unknown provider: {t.provider}")


@dataclass
class _ErrorProvider(Provider):
    error: str

    async def run_iteration(
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


def _load_run_status(store: ArtifactStore) -> RunStatus | None:
    try:
        data = store.read_json("RUN_STATUS.json")
        return RunStatus(**data)
    except Exception:
        return None


async def run_debug_session(cfg: RunConfig) -> RunResult:
    store = ArtifactStore(cfg.run_dir())
    store.ensure()
    ev = EventLog(store.path("events.jsonl"))

    try:
        # Resume logic
        existing_status = None
        if cfg.resume:
            existing_status = _load_run_status(store)
            if existing_status and existing_status.status in ("OK", "DONE", "FAIL"):
                # Already done?
                # User might want to retry a failed run, but for now we just warn.
                pass
        
        # Hydrate issue_text if resuming or missing
        issue_text = cfg.issue_text
        if not issue_text and cfg.resume:
            # Prefer RUN.json if it contains issue_text (forward/backward compatible)
            try:
                run_json = store.read_json("RUN.json")
                if isinstance(run_json, dict) and "issue_text" in run_json and run_json["issue_text"]:
                    issue_text = str(run_json["issue_text"])
            except Exception:
                # Fallback: leave issue_text empty and rely on existing artifacts to skip steps
                pass

        tracks, use_ts, max_files = _load_tracks(cfg)
        wt = WorktreeManager(repo=cfg.repo_path, store=store)

        if not cfg.resume:
            meta = RunMeta(
                run_id=cfg.run_id,
                repo_path=str(cfg.repo_path),
                mode=cfg.mode,
                issue_text_present=bool(issue_text),
                issue_text=issue_text,  # Store for resume
                use_docker=cfg.use_docker,
                use_treesitter=use_ts,
                tracks=[t.__dict__ for t in tracks],
            )
            store.write_run_meta(meta)
            status = RunStatus(run_id=cfg.run_id, mode=cfg.mode, status="RUNNING", message="starting")
            store.write_status(status)
        else:
            ev.emit(stage="resume", action="load_state", run_id=cfg.run_id)

        # Setup worktrees (best effort)
        # Idempotent
        ev.emit(stage="setup", action="worktrees_create")
        wt.create_worktrees([t.name for t in tracks])
        wt.write_worktree_contracts(tracks)

        # Steps - Skip if artifacts allow
        # ContextBuilder checks if CONTEXT.md exists internally? No, we should check here to skip.
        if not (store.path("CONTEXT.md").exists() and cfg.resume):
            ContextBuilder().run(
                store, cfg.repo_path, issue_text=issue_text or "", use_treesitter=use_ts, max_files=max_files
            )
        
        if ContextBuilder().check(store, cfg.repo_path) != 0:
            store.write_status(
                RunStatus(
                    run_id=cfg.run_id, mode=cfg.mode, status="FAIL", message="context check failed"
                )
            )
            return RunResult(status="FAIL", run_dir=store.run_dir)

        # Repro Assessment (Track 0 - determine reproduction strategy)
        repro_mode = "MANUAL"  # default
        if not (store.path("REPRO_ASSESS.json").exists() and cfg.resume):
            ev.emit(stage="repro_assess", action="run")
            repro_result = ReproAssess().run(store, cfg.repo_path, issue_text=issue_text)
            repro_mode = repro_result.mode.value
            ev.emit(stage="repro_assess", action="done", mode=repro_mode)
        else:
            # Read from existing
            try:
                import json
                data = json.loads(store.path("REPRO_ASSESS.json").read_text())
                repro_mode = data.get("repro_mode", "MANUAL")
            except Exception:
                pass

        if not (store.path("REPRO.md").exists() and cfg.resume):
            ReproPlan().run(store, cfg.repo_path, issue_text=issue_text or "")
            
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

        # Iterate each track
        # TODO: Better resume support for partial track completion (checking per-track iteration artifacts)
        # For now, we rerun track iteration if not fully done? 
        # Or we rely on provider/step idempotency? TrackIterate calls provider.run_iteration.
        # If we re-run, we might overwrite. 
        # Prudent resume: if track has ANY iteration, skip it? Or continue?
        # Let's simple-skip if `store.path("tracks", t.name, "iter_1", "ITERATION.json").exists()`
        
        async def _process_track(t: TrackConfig) -> None:
            max_iters = t.budgets.max_iters
            current_iter = 1
            
            # Resume logic: find last successfully completed iteration
            # Check both ITERATION.json existence AND CHECK_iterate.json with exit_code==0
            if cfg.resume:
                # Find last completed AND validated iteration
                last_completed = 0
                for i in range(1, max_iters + 1):
                    iter_path = store.path("tracks", t.name, f"iter_{i:02d}", "ITERATION.json")
                    check_path = store.path("tracks", t.name, f"iter_{i:02d}", "CHECK_iterate.json")
                    
                    if not iter_path.exists():
                        break
                    
                    # Also verify the check passed (exit_code == 0)
                    if check_path.exists():
                        try:
                            import json
                            check_data = json.loads(check_path.read_text())
                            if check_data.get("exit_code", 2) != 0:
                                # This iteration failed validation, don't count it
                                break
                        except Exception:
                            # If we can't read check file, assume invalid
                            break
                    # If no CHECK file exists, we assume it hasn't been checked yet
                    # so we should rerun from here (conservative)
                    elif iter_path.exists():
                        # ITERATION.json exists but no CHECK - need to rerun check
                        break
                    
                    last_completed = i
                current_iter = last_completed + 1
            
            if current_iter > max_iters:
                return

            try:
                try:
                    provider = _provider_for_track(t)
                except Exception as exc:
                    provider = _ErrorProvider(error=f"Provider init failed for {t.provider}: {exc}")
                
                iter_step = TrackIterate()
                
                for iteration in range(current_iter, max_iters + 1):
                    ev.emit(
                        stage="iterate",
                        track=t.name,
                        iter=iteration,
                        action="provider_call",
                        provider=t.provider,
                        model=t.model or "",
                    )
                    
                    bb_path = store.path("BLACKBOARD.md")
                    current_bb = bb_path.read_text(encoding="utf-8", errors="ignore") if bb_path.exists() else ""
                    


                    await iter_step.run(
                        store=store,
                        repo=wt.get_worktree_path(t.name),
                        track=t.name,
                        role=t.role,
                        provider=provider,
                        iteration=iteration,
                        directions_profile=t.directions_profile,
                        context_text=context_text,
                        blackboard_text=current_bb,
                    )
                    
                    # Opportunistic Verification (for Judge signals)
                    patch_path = store.path("tracks", t.name, f"iter_{iteration:02d}", "PATCH.diff")
                    if patch_path.exists():
                        wt_path = wt.get_worktree_path(t.name)
                        try:
                            # 1. Apply patch
                            apply_cmd = f'git apply --whitespace=nowarn "{patch_path}"'
                            apply_res = run_cmd(apply_cmd, cwd=wt_path, timeout_s=30)
                            
                            if apply_res.returncode == 0:
                                # 2. Run Verify
                                iter_store = ArtifactStore(store.path("tracks", t.name, f"iter_{iteration:02d}"))
                                Verify().run(iter_store, wt_path)
                            
                            # 3. Revert (clean up worktree for next iteration)
                            # We assume next iteration starts from clean state + potentially previous valid patch?
                            # Current Anvil doesn't support cumulative patches in loop yet (stateless iterations).
                            run_cmd("git checkout .", cwd=wt_path)
                        except Exception:
                            pass
                    
                    chk = TrackIterate().check(store, cfg.repo_path, track=t.name, iteration=iteration)
                    if chk != 0:
                        disqualified.append(t.name)
                        ev.emit(
                            stage="iterate",
                            track=t.name,
                            iter=iteration,
                            action="disqualified",
                            reason="iterate_check_failed",
                        )
                        break

                    try:
                        p_json = store.path("tracks", t.name, f"iter_{iteration:02d}", "ITERATION.json")
                        import json
                        data = json.loads(p_json.read_text())
                        signal = data.get("status_signal", "CONTINUE")
                        if signal == "DONE":
                            ev.emit(stage="iterate", track=t.name, iter=iteration, action="done")
                            Blackboard().write(store, [tr.name for tr in tracks])
                            break
                    except Exception:
                        pass
                    
                    Blackboard().write(store, [tr.name for tr in tracks])

            except Exception as exc:
                disqualified.append(t.name)
                ev.emit(stage="iterate", track=t.name, action="crash", error=str(exc))
                store.path("tracks", t.name).mkdir(parents=True, exist_ok=True)
                store.write_text(
                    store.path("tracks", t.name, "CRASH.txt"),
                    traceback.format_exc(),
                )

        # Run all tracks concurrently
        results = await asyncio.gather(*[_process_track(t) for t in tracks], return_exceptions=True)
        for t, r in zip(tracks, results):
            if isinstance(r, Exception):
                if t.name not in disqualified:
                    disqualified.append(t.name)
                ev.emit(stage="iterate", track=t.name, action="crash", error=str(r))

        # Build blackboard (observations-only)
        Blackboard().write(store, [t.name for t in tracks])
        blackboard_text = store.path("BLACKBOARD.md").read_text(encoding="utf-8", errors="ignore")

        # Verify
        # If verify already run? Verify is cheap enough to re-run usually, implies freshness.
        ev.emit(stage="verify", action="run")
        Verify().run(store, cfg.repo_path, use_docker=cfg.use_docker)
        Verify().check(store, cfg.repo_path)

        # Score (artifact-backed)
        ScoreComputer().write(store, [t.name for t in tracks])

        # Judge
        ev.emit(stage="judge", action="run")
        tracks_map = {t.name: t for t in tracks}
        decision = Judge().run(store, [t.name for t in tracks], disqualified=disqualified, tracks_config=tracks_map)
        Judge().check(store, cfg.repo_path)

        # Apply (only if we have a patch and ANVIL_AUTO_APPLY is enabled)
        import os
        auto_apply = os.environ.get("ANVIL_AUTO_APPLY", "1").lower() in ("1", "true", "yes")
        winner = decision.winner
        applied = False
        if winner and auto_apply:
            patches = sorted(store.path("tracks", winner).glob("iter_*/PATCH.diff"))
            if patches:
                patch = patches[-1]
                ev.emit(stage="apply", action="run", winner=winner, patch=str(patch))
                rc = Apply().run(store, cfg.repo_path, patch_path=patch)
                applied = rc == 0
        elif winner and not auto_apply:
            ev.emit(stage="apply", action="skipped", reason="ANVIL_AUTO_APPLY disabled")

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


async def run_harden_session(cfg: RunConfig) -> RunResult:
    """Run a hardening session with parallel breaker tracks.
    
    Harden mode goal: Find vulnerabilities, suggest tests, improve code quality.
    Unlike debug mode (fix a known bug), harden mode proactively finds issues.
    """
    store = ArtifactStore(cfg.run_dir())
    store.ensure()
    ev = EventLog(store.path("events.jsonl"))

    try:
        tracks, use_ts, max_files = _load_tracks(cfg)
        
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
        store.write_status(
            RunStatus(run_id=cfg.run_id, mode=cfg.mode, status="RUNNING", message="starting harden")
        )

        # Step 1: Build context (same as debug but may focus on different aspects)
        ev.emit(stage="harden", action="context")
        ctx_chk = ContextBuilder().check(store, cfg.repo_path)
        if ctx_chk != 0:
            ContextBuilder().run(
                store,
                cfg.repo_path,
                issue_text=cfg.issue_text or "Harden this codebase: find bugs, vulnerabilities, missing tests.",
                use_treesitter=use_ts,
                max_files=max_files,
            )
        
        context_md = store.path("CONTEXT.md").read_text(encoding="utf-8", errors="ignore")
        
        # Step 2: Baseline verification
        ev.emit(stage="harden", action="verify_baseline")
        Verify().run(store, cfg.repo_path, use_docker=cfg.use_docker)
        
        baseline_verify = (
            store.path("VERIFY.md").read_text(encoding="utf-8", errors="ignore")
            if store.path("VERIFY.md").exists()
            else "No baseline verification ran."
        )
        
        # Step 3: Setup worktrees for breaker tracks
        wt = WorktreeManager(repo=cfg.repo_path, store=store)
        wt.create_worktrees([t.name for t in tracks])
        wt.write_worktree_contracts(tracks)
        
        # Step 4: Create harden-specific blackboard with baseline info
        harden_blackboard = [
            "# Harden Blackboard",
            "",
            "## Objective",
            "Find vulnerabilities, missing tests, edge cases, and code quality issues.",
            "",
            "## Baseline Verification",
            baseline_verify[:2000] if len(baseline_verify) > 2000 else baseline_verify,
        ]
        store.write_text("BLACKBOARD.md", "\n".join(harden_blackboard))
        
        findings: dict[str, list[str]] = {}
        disqualified: list[str] = []
        
        # Step 5: Run parallel breaker tracks
        async def _process_breaker_track(t: TrackConfig) -> None:
            max_iters = t.budgets.max_iters
            track_findings: list[str] = []
            
            try:
                try:
                    provider = _provider_for_track(t)
                except Exception as exc:
                    provider = _ErrorProvider(error=f"Provider init failed: {exc}")
                
                iter_step = TrackIterate()
                
                for iteration in range(1, max_iters + 1):
                    ev.emit(
                        stage="harden_iterate",
                        track=t.name,
                        iter=iteration,
                        action="breaker_call",
                    )
                    
                    bb_path = store.path("BLACKBOARD.md")
                    current_bb = bb_path.read_text(encoding="utf-8", errors="ignore") if bb_path.exists() else ""
                    
                    await iter_step.run(
                        store=store,
                        repo=wt.get_worktree_path(t.name),
                        track=t.name,
                        role=t.role or "breaker",
                        directions_profile="harden",
                        context_text=context_md[:15000],
                        blackboard_text=current_bb,
                        iteration=iteration,
                        provider=provider,
                    )
                    
                    # Check iteration result
                    chk = iter_step.check(store, cfg.repo_path, track=t.name, iteration=iteration)
                    if chk != 0:
                        if t.name not in disqualified:
                            disqualified.append(t.name)
                        ev.emit(stage="harden_iterate", track=t.name, action="disqualified", reason="iterate_check_failed")
                        break
                    
                    # Read findings from iteration
                    iter_json_path = store.path("tracks", t.name, f"iter_{iteration:02d}", "ITERATION.json")
                    if iter_json_path.exists():
                        import json
                        try:
                            iter_data = json.loads(iter_json_path.read_text(encoding="utf-8"))
                        except Exception:
                            iter_data = {}
                        
                        if iter_data.get("hypothesis"):
                            track_findings.append(f"[Iter {iteration}] {iter_data['hypothesis']}")
                        
                        # Check for DONE signal
                        if iter_data.get("status_signal") == "DONE":
                            break
                    
                    # Update blackboard with findings from ALL tracks (not just this one)
                    Blackboard().write(store, [tr.name for tr in tracks])
            
            except Exception as exc:
                # Per-track crash isolation: do not crash whole harden session
                if t.name not in disqualified:
                    disqualified.append(t.name)
                ev.emit(stage="harden_iterate", track=t.name, action="crash", error=str(exc))
                store.path("tracks", t.name).mkdir(parents=True, exist_ok=True)
                store.write_text(
                    store.path("tracks", t.name, "CRASH.txt"),
                    traceback.format_exc(),
                )
            
            findings[t.name] = track_findings
        
        # Run all breaker tracks in parallel (do not crash harden if one fails)
        ev.emit(stage="harden", action="parallel_breakers", num_tracks=len(tracks))
        results = await asyncio.gather(*[_process_breaker_track(t) for t in tracks], return_exceptions=True)
        for t, r in zip(tracks, results):
            if isinstance(r, Exception):
                if t.name not in disqualified:
                    disqualified.append(t.name)
                ev.emit(stage="harden_iterate", track=t.name, action="crash", error=str(r))
                store.path("tracks", t.name).mkdir(parents=True, exist_ok=True)
                store.write_text(
                    store.path("tracks", t.name, "CRASH.txt"),
                    "".join(traceback.format_exception(type(r), r, r.__traceback__)),
                )
        
        # Step 6: Compile HARDEN.md report
        harden_report = [
            "# HARDEN Report",
            "",
            f"Run ID: `{cfg.run_id}`",
            f"Tracks: {len(tracks)}",
            f"Disqualified: {len(disqualified)}",
            "",
            "## Baseline Verification",
            "",
            baseline_verify[:3000] if len(baseline_verify) > 3000 else baseline_verify,
            "",
            "## Findings by Track",
            "",
        ]
        
        for track_name, track_findings in findings.items():
            harden_report.append(f"### {track_name}")
            if track_name in disqualified:
                harden_report.append("**DISQUALIFIED**")
            if track_findings:
                for f in track_findings:
                    harden_report.append(f"- {f}")
            else:
                harden_report.append("No findings.")
            harden_report.append("")
        
        # List any patches generated
        harden_report.append("## Generated Patches")
        harden_report.append("")
        for t in tracks:
            for i in range(1, t.budgets.max_iters + 1):
                patch_path = store.path("tracks", t.name, f"iter_{i:02d}", "PATCH.diff")
                if patch_path.exists():
                    harden_report.append(f"- `{patch_path.relative_to(store.run_dir)}`")
        
        store.write_text("HARDEN.md", "\n".join(harden_report))
        
        store.write_status(
            RunStatus(
                run_id=cfg.run_id, 
                mode=cfg.mode, 
                status="DONE", 
                message=f"harden completed, {len(findings)} tracks processed",
                disqualified_tracks=disqualified,
            )
        )
        return RunResult(status="DONE", run_dir=store.run_dir, decision_file=store.path("HARDEN.md"))
    except Exception as exc:  # pragma: no cover
        ev.emit(stage="crash", action="exception", error=str(exc))
        store.write_text("CRASH.txt", traceback.format_exc())
        store.write_status(
            RunStatus(run_id=cfg.run_id, mode=cfg.mode, status="FAIL", message=f"crash: {exc}")
        )
        return RunResult(status="FAIL", run_dir=store.run_dir)

