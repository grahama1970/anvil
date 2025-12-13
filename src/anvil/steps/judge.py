"""Judge step (evidence-weighted, blind-ish).

CONTRACT
- Inputs: Run artifacts (ITERATION.json, VERIFY.md, PATCH.diff)
- Outputs (required):
  - SCORECARD.json (scores per track)
  - DECISION.md (winner explanation)
- Invariants:
  - Disqualified tracks cannot win.
  - Scoring is hybrid: Confidence (provider self-report) + Evidence (Patch existence).
  - Winner requires positive score (>0).
- Failure:
  - Returns JudgeDecision with winner=None if no positive scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..artifacts.schemas import JudgeDecision
from ..artifacts.store import ArtifactStore
from ..contracts.validate import check_required_artifacts

from ..config import TrackConfig


@dataclass
class Judge:
    name: str = "judge"

    def run(
        self,
        store: ArtifactStore,
        candidate_tracks: list[str],
        disqualified: list[str],
        tracks_config: dict[str, TrackConfig] | None = None
    ) -> JudgeDecision:
        scores: dict[str, float] = {}
        track_details: dict[str, list[str]] = {}

        for t in candidate_tracks:
            if t in disqualified:
                scores[t] = -1e9
                continue

            score = 0.0
            details = []

            # 1. Per-track verification (in worktree artifacts)
            # The verify step runs in worktrees, but orchestrator might only run global verify?
            # Orchestrator currently runs global Verify() at the end.
            # But wait, Verify() step might be checking the *repo* state.
            # If Verify passes globally, does it mean all tracks passed? No, global verify checks HEAD.
            # But tracks have their own patches.
            # Orchestrator does NOT currently apply patches for verification of each track individually in the loop.
            # But wait, Verify() checks `repro_script`.
            # If we rely on global verify, we only know if the repo *currently* passes.
            # But the repo might be clean or dirty.

            # Task 3.2 says: "Run verification per-worktree OR use per-track metrics"
            # Since we assume the agent ran verification in its loop (not implemented yet fully in orchestrator logic for per-track)
            # We will check if `VERIFY.md` exists in the track's artifact folder (from `TrackIterate` or similar).
            # Currently `TrackIterate` doesn't run verify explicitly.
            # BUT, the global verify runs at the end.
            # If we want per-track, we should look at `ITERATION.json` for self-reported verification?

            # Let's use `confidence` from ITERATION.json as primary signal + global verify if applicable.
            # And check if the track produced a valid patch.

            tdir = store.path("tracks", t)

            # Latest iteration
            iters = sorted(tdir.glob("iter_*/ITERATION.json"))
            confidence = 0.0
            if iters:
                latest_iter = iters[-1]
                try:
                    import json
                    data = json.loads(latest_iter.read_text())
                    confidence = float(data.get("confidence", 0.0))
                    # Clamp 0-1
                    confidence = max(0.0, min(1.0, confidence))
                    score += confidence * 50.0 # Weighted confidence
                    details.append(f"Confidence {confidence:.2f} (+{confidence * 50.0:.1f})")
                except Exception:
                    details.append("Error reading confidence")

            # Role detection via config (preferred) -> iteration artifact (fallback) -> default
            track_role = "fixer"
            if tracks_config and t in tracks_config:
                track_role = tracks_config[t].role.lower()
            elif iters:
                # Fallback to iteration metadata if config missing
                try:
                    # Some providers/prompts might accept 'role' in meta, but we haven't standardized saving it in JSON body yet.
                    pass
                except Exception:
                    pass

            is_fixer = track_role in ("fixer", "debugger", "backend_fixer", "frontend_fixer")

            # Patch presence
            patches = list(tdir.glob("iter_*/PATCH.diff"))
            if patches:
                score += 20.0
                details.append("Patch found (+20)")
            else:
                # Only penalize fixer roles heavily for missing patches
                if is_fixer:
                    score -= 50.0
                    details.append(f"No patch (-50, {track_role} role)")
                else:
                    # Breaker/explorer tracks: small penalty or neutral
                    score -= 10.0
                    details.append(f"No patch (-10, {track_role} role)")

            # Per-track VERIFY.md existence and signal
            verify_files = sorted(tdir.glob("iter_*/VERIFY.md"))
            if verify_files:
                score += 10.0  # small bonus for having run verification
                details.append("Verification artifact found (+10)")
                try:
                    vtext = verify_files[-1].read_text().upper()
                    if "PASS" in vtext:
                        score += 50.0
                        details.append("Verification PASS (+50)")
                    elif "FAIL" in vtext:
                        # Fixer tracks: Heavy penalty for failing tests (never accept a breaking change)
                        if is_fixer:
                            score -= 100.0
                            details.append("Verification FAIL (-100, fixer role)")
                        else:
                            # Breaker: failing tests might mean it found a bug, so less penalty?
                            # But usually breaker wants to *demonstrate* failure. 
                            # If it claims to work but verification fails (crash?), it's bad.
                            # But if the GOAL was to break it...
                            # Actually, normally breaker generates a test that FAILS on current code.
                            # If Anvil runs that test and it FAILS, that might be SUCCESS for a breaker.
                            # But current verify logic is: run *all* tests.
                            # Let's keep -40 for others for now.
                            score -= 40.0
                            details.append("Verification FAIL (-40)")
                except Exception:
                    details.append("Error reading VERIFY.md")

            # Global verify pass? (Assuming the last applied verify was this track? No, wait.)
            # If orchestrator runs verify *after* all tracks, it's checking the *base* repo usually, or the last applied patch?
            # Actually Orchestrator currently runs Verify() on `cfg.repo_path`.
            # If no patch applied, it checks base.
            # So global verify is not useful for distinguishing tracks yet.
            # We will assume confident tracks with patches are better.
            
            scores[t] = score
            track_details[t] = details

        winner: str | None = None
        best = -1e18
        # Simple max
        for t, s in scores.items():
            if s > best and s > 0: # Must be positive to win
                best = s
                winner = t
            elif s > best:
                 best = s # Track best score even if negative, but don't pick winner if all negative
        
        reason = f"Selected {winner} based on confidence and patch presence."
        decision = JudgeDecision(
            winner=winner, reason=reason, scores=scores, disqualified=disqualified
        )
        store.write_json("SCORECARD.json", decision.model_dump())

        md = [
            "# DECISION",
            "",
            f"Winner: **{winner or 'NONE'}**",
            "",
            "## Reason",
            reason,
            "",
            "## Scores",
        ]
        for t, s in scores.items():
            md.append(f"- {t}: {s:.1f}")
            # Include track details for transparency ("no vibes")
            if t in track_details:
                for detail in track_details[t]:
                    md.append(f"  - {detail}")
        if disqualified:
            md += ["", "## Disqualified", "", ", ".join(disqualified)]
        store.write_text("DECISION.md", "\n".join(md) + "\n")

        return decision

    def check(self, store: ArtifactStore, repo: Path) -> int:
        res = check_required_artifacts(store.run_dir, ["SCORECARD.json", "DECISION.md"])
        store.write_json("CHECK_judge.json", res.model_dump())
        return 0 if res.ok else 1

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Judge Step")
    parser.add_argument("--candidates", required=True, nargs="+", help="List of candidate tracks")
    parser.add_argument("--disqualified", nargs="+", default=[], help="List of disqualified tracks")
    parser.add_argument("--out-dir", required=True, help="Output directory for artifacts")
    args = parser.parse_args()

    try:
        store = ArtifactStore(Path(args.out_dir))
        step = Judge()
        decision = step.run(store, args.candidates, args.disqualified)
        print(f"Winner: {decision.winner}")
        sys.exit(step.check(store, Path(".")))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
