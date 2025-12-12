from __future__ import annotations

from dataclasses import dataclass

from ..artifacts.store import ArtifactStore


@dataclass
class ScoreComputer:
    """Compute artifact-backed scores (no vibes)."""

    def score_track(self, store: ArtifactStore, track: str) -> float:
        score = 0.0
        tdir = store.path("tracks", track)

        # Evidence: has any ITERATION.json
        iters = list(tdir.glob("iter_*/ITERATION.json"))
        if iters:
            score += 5.0

        # Evidence: has PATCH.diff
        patches = list(tdir.glob("iter_*/PATCH.diff"))
        if patches:
            score += 10.0

        # Verification: PASS?
        verify_md = store.path("VERIFY.md")
        if verify_md.exists():
            txt = verify_md.read_text(encoding="utf-8", errors="ignore")
            if "PASS" in txt and "FAIL" not in txt:
                score += 40.0

        # Disqualification handled elsewhere.
        return score

    def write(self, store: ArtifactStore, tracks: list[str]) -> None:
        data = {"schema_version": 1, "scores": {t: self.score_track(store, t) for t in tracks}}
        store.write_json("SCORES.json", data)
