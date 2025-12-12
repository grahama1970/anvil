from __future__ import annotations

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


def load_tracks_file(path: Path) -> TracksFileConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    tracks_raw = data.get("tracks", [])
    tracks: list[TrackConfig] = []
    for t in tracks_raw:
        b = t.get("budgets", {}) or {}
        budgets = TrackBudget(
            max_iters=int(b.get("max_iters", 3)), max_calls=int(b.get("max_calls", 12))
        )
        tracks.append(
            TrackConfig(
                name=validate_track_name(str(t["name"])),
                role=str(t.get("role", "explorer")),
                provider=str(t.get("provider", "manual")),
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
