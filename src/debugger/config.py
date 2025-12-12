from __future__ import annotations

"""Configuration models.

CONTRACT
- Inputs: YAML file path (tracks.yaml) or dictionary data
- Outputs (required):
  - Validated RunConfig, TracksFileConfig, TrackConfig objects
- Invariants:
  - Track names match `[A-Za-z0-9][A-Za-z0-9_-]{0,31}`
  - Default values are safe (manual provider, safe budgets)
- Failure:
  - Raises ValueError/ValidationError on invalid schema or names
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from .util.ids import validate_track_name

Mode = Literal["debug", "harden"]


@dataclass(frozen=True)
class TrackBudget:
    max_iters: int = 3
    max_calls: int = 12


@dataclass(frozen=True)
class TrackConfig:
    name: str
    role: str
    provider: str
    model: str | None = None
    directions_profile: str = "strict_minimal_patch"
    budgets: TrackBudget = field(default_factory=TrackBudget)
    provider_options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyConfig:
    mode: str = "auto_escalate"
    max_tracks: int = 4
    spawn_breaker: bool = True
    escalate_if: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class CollabConfig:
    mode: str = "observations"
    sync_every_iters: int = 2


@dataclass(frozen=True)
class ContextConfig:
    use_treesitter: bool = False
    max_files: int = 25


@dataclass(frozen=True)
class TracksFileConfig:
    tracks: list[TrackConfig]
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    collab: CollabConfig = field(default_factory=CollabConfig)
    context: ContextConfig = field(default_factory=ContextConfig)


@dataclass(frozen=True)
class RunConfig:
    repo_path: Path
    run_id: str
    artifacts_root: Path
    tracks_file: Path | None
    issue_text: str | None
    mode: Mode
    use_docker: bool = False
    use_treesitter: bool = False
    resume: bool = False
    candidate_run: str | None = None
    candidate_track: str | None = None

    def run_dir(self) -> Path:
        return self.artifacts_root / self.run_id


TRACKS_SCHEMA = {
    "type": "object",
    "properties": {
        "tracks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$"},
                    "role": {"type": "string"},
                    "provider": {
                        "type": "string",
                        "enum": ["manual", "copilot", "gemini", "gh_cli"]
                    },
                    "model": {"type": ["string", "null"]},
                    "directions_profile": {"type": "string"},
                    "provider_options": {"type": "object"},
                    "budgets": {
                        "type": "object",
                        "properties": {
                            "max_iters": {"type": "integer"},
                            "max_calls": {"type": "integer"}
                        }
                    }
                },
                "required": ["name"]
            }
        },
        "policy": {"type": "object"},
        "collab": {"type": "object"},
        "context": {"type": "object"},
    },
    "required": ["tracks"]
}

def load_tracks_file(path: Path) -> TracksFileConfig:
    import jsonschema  # lazy import
    
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    
    # Task 4.8: Validate schema
    try:
        jsonschema.validate(instance=data, schema=TRACKS_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Invalid tracks.yaml schema: {e.message}") from e

    tracks_raw = data.get("tracks", [])
    tracks: list[TrackConfig] = []
    for t in tracks_raw:
        b = t.get("budgets", {}) or {}
        budgets = TrackBudget(
            max_iters=int(b.get("max_iters", 3)), max_calls=int(b.get("max_calls", 12))
        )
        provider = str(t.get("provider", "manual"))
        tracks.append(
            TrackConfig(
                name=validate_track_name(str(t["name"])),
                role=str(t.get("role", "explorer")),
                provider=provider,
                model=t.get("model", None),
                directions_profile=str(t.get("directions_profile", "strict_minimal_patch")),
                budgets=budgets,
                provider_options=dict(t.get("provider_options", {}) or {}),
            )
        )
    policy_raw = data.get("policy", {}) or {}
    collab_raw = data.get("collab", {}) or {}
    context_raw = data.get("context", {}) or {}
    return TracksFileConfig(
        tracks=tracks,
        policy=PolicyConfig(
            mode=str(policy_raw.get("mode", "auto_escalate")),
            max_tracks=int(policy_raw.get("max_tracks", 4)),
            spawn_breaker=bool(policy_raw.get("spawn_breaker", True)),
            escalate_if=list(policy_raw.get("escalate_if", [])),
        ),
        collab=CollabConfig(
            mode=str(collab_raw.get("mode", "observations")),
            sync_every_iters=int(collab_raw.get("sync_every_iters", 2)),
        ),
        context=ContextConfig(
            use_treesitter=bool(context_raw.get("use_treesitter", False)),
            max_files=int(context_raw.get("max_files", 25)),
        ),
    )


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Config Loader CLI")
    parser.add_argument("--tracks", required=True, help="Path to tracks.yaml")
    args = parser.parse_args()

    try:
        cfg = load_tracks_file(Path(args.tracks))
        # Dump as simple dict (requires handling nested dataclasses if complex, but simple here)
        # Using simple print for structure check
        print(f"Loaded {len(cfg.tracks)} tracks.")
        print(f"Policy: {cfg.policy}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
