from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..artifacts.store import ArtifactStore


@dataclass
class Blackboard:
    """Observations-only blackboard builder."""

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
