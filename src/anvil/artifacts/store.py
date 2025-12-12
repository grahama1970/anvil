from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schemas import RunMeta, RunStatus


@dataclass(frozen=True)
class ArtifactStore:
    """Artifact storage manager.

    CONTRACT
    - Inputs: Run directory path
    - Outputs:
      - Writes files to .dbg/runs/<id>/...
    - Invariants:
      - Enforces path safety (prevents traversal outside run_dir)
      - Ensures parent directories exist on write
    - Failure:
      - Raises ValueError on unsafe path access
    """
    run_dir: Path

    def ensure(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "tracks").mkdir(exist_ok=True)
        (self.run_dir / "logs").mkdir(exist_ok=True)

    def path(self, *parts: str) -> Path:
        p = self.run_dir.joinpath(*parts)
        base = self.run_dir.resolve(strict=False)
        try:
            p.resolve(strict=False).relative_to(base)
        except ValueError as exc:
            raise ValueError(f"Refusing to access path outside run_dir: {p}") from exc
        return p

    def write_json(self, rel: str, data: Any) -> Path:
        p = self.path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return p

    def read_json(self, rel: str) -> Any:
        p = self.path(rel)
        return json.loads(p.read_text(encoding="utf-8"))

    def write_text(self, rel: str, text: str) -> Path:
        p = self.path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def write_run_meta(self, meta: RunMeta) -> Path:
        return self.write_json("RUN.json", meta.model_dump())

    def write_status(self, status: RunStatus) -> Path:
        return self.write_json("RUN_STATUS.json", status.model_dump())

    def append_progress_line(self, track: str, line: str) -> None:
        p = self.path("tracks", track, "PROGRESS.md")
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Artifact Store CLI")
    parser.add_argument("--run-dir", required=True, help="Path to run directory")
    parser.add_argument("--ensure", action="store_true", help="Ensure directory exists")
    args = parser.parse_args()

    try:
        store = ArtifactStore(Path(args.run_dir))
        if args.ensure:
            store.ensure()
            print(f"Ensured {args.run_dir}")
        else:
            print("No action specified. Use --ensure.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
