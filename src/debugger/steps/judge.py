"""Judge step (evidence-weighted, blind-ish).

CONTRACT
- Inputs: artifacts under tracks/*
- Outputs (required):
  - SCORECARD.json
  - DECISION.md
- Rule:
  - Disqualified tracks cannot win.
  - Prefer tracks with VERIFY PASS.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..artifacts.schemas import JudgeDecision
from ..artifacts.store import ArtifactStore
from ..contracts.validate import check_required_artifacts


@dataclass
class Judge:
    name: str = "judge"

    def run(
        self, store: ArtifactStore, candidate_tracks: list[str], disqualified: list[str]
    ) -> JudgeDecision:
        # Evidence: did verification pass? does track have PATCH?
        verify_md = store.path("VERIFY.md")
        verify_pass = False
        if verify_md.exists():
            txt = verify_md.read_text(encoding="utf-8", errors="ignore")
            verify_pass = "PASS" in txt and "FAIL" not in txt

        scores: dict[str, float] = {}
        for t in candidate_tracks:
            if t in disqualified:
                scores[t] = -1e9
                continue
            # Minimal scoring: verified pass + patch presence.
            score = 0.0
            if verify_pass:
                score += 100.0
            # Find latest patch
            patches = list(store.path("tracks", t).glob("iter_*/PATCH.diff"))
            if patches:
                score += 10.0
            scores[t] = score

        winner: str | None = None
        best = -1e18
        for t, s in scores.items():
            if s > best:
                best = s
                winner = t if t not in disqualified else None

        reason = "Selected highest evidence score (verify pass + patch presence)."
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
            md.append(f"- {t}: {s}")
        if disqualified:
            md += ["", "## Disqualified", "", ", ".join(disqualified)]
        store.write_text("DECISION.md", "\n".join(md) + "\n")

        return decision

    def check(self, store: ArtifactStore, repo: Path) -> int:
        res = check_required_artifacts(store.run_dir, ["SCORECARD.json", "DECISION.md"])
        store.write_json("CHECK_judge.json", res.model_dump())
        return res.exit_code
