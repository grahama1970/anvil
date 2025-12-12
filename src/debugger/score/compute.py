from __future__ import annotations

from dataclasses import dataclass

from ..artifacts.store import ArtifactStore


@dataclass
class ScoreComputer:
    """Compute artifact-backed scores (no vibes).

    CONTRACT
    - Inputs: ArtifactStore, list of tracks
    - Outputs (required):
      - SCORES.json
    - Invariants:
      - Scoring is deterministic based on file presence/content
      - +5 for ITERATION.json, +10 for PATCH.diff, +40 for VERIFY PASS
    - Failure:
      - Returns 0.0 for tracks with missing artifacts
    """

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


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Score Computer CLI")
    parser.add_argument("--run-dir", required=True, help="Path to run directory")
    parser.add_argument("--tracks", nargs="+", required=True, help="List of tracks")
    args = parser.parse_args()

    try:
        store = ArtifactStore(Path(args.run_dir))
        sc = ScoreComputer()
        sc.write(store, args.tracks)
        print("Generated SCORES.json")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
