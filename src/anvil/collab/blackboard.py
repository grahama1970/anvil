from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..artifacts.store import ArtifactStore


@dataclass
class Blackboard:
    """Observations-only blackboard builder.

    CONTRACT
    - Inputs: ArtifactStore, list of tracks
    - Outputs (required):
      - BLACKBOARD.md
      - BLACKBOARD.json (observations only)
    - Invariants:
      - Reads latest ITERATION.json for each track
      - Extracts only public observations (status, hypothesis, experiments, risks)
    - Failure:
      - Skips tracks with missing/invalid artifacts (best-effort)
    """

    def build(self, store: ArtifactStore, tracks: list[str]) -> dict[str, Any]:
        obs: dict[str, Any] = {"schema_version": 1, "tracks": {}}
        for t in tracks:
            tdir = store.path("tracks", t)
            iters = sorted(tdir.glob("iter_*/ITERATION.json"))
            last = iters[-1] if iters else None
            if not last:
                continue
            try:
                raw = json.loads(last.read_text(encoding="utf-8"))
            except Exception:
                continue
            # observations-only extraction
            obs["tracks"][t] = {
                "iteration": raw.get("iteration"),
                "status_signal": raw.get("status_signal"),
                "hypothesis": raw.get("hypothesis"),
                "experiments": raw.get("experiments", []),
                "risks": raw.get("risks", []),
            }
        return obs

    def write(self, store: ArtifactStore, tracks: list[str]) -> None:
        data = self.build(store, tracks)
        store.write_json("BLACKBOARD.json", data)
        md = ["# BLACKBOARD (observations-only)", ""]
        for t, v in (data.get("tracks") or {}).items():
            md += [
                f"## {t}",
                f"- iteration: {v.get('iteration')}",
                f"- status: {v.get('status_signal')}",
                "",
            ]
            md += [f"- hypothesis: {v.get('hypothesis')}", ""]
            md += ["### experiments", ""]
            for e in v.get("experiments", []):
                md.append(f"- {e.get('name')} — cmd: `{e.get('command')}`")
            md += ["", "### risks", ""]
            for r in v.get("risks", []):
                md.append(f"- {r}")
            md.append("")
        store.write_text("BLACKBOARD.md", "\n".join(md))


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Blackboard CLI")
    parser.add_argument("--run-dir", required=True, help="Path to run directory")
    parser.add_argument("--tracks", nargs="+", required=True, help="List of tracks")
    # Note: Using simpler CLI that assumes store/files exist
    args = parser.parse_args()

    try:
        store = ArtifactStore(Path(args.run_dir))
        bb = Blackboard()
        bb.write(store, args.tracks)
        print("Generated BLACKBOARD.md and BLACKBOARD.json")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
