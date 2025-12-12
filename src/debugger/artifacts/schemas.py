from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RunStatus(BaseModel):
    schema_version: int = 1
    run_id: str
    mode: Literal["debug", "harden"]
    status: str
    message: str = ""
    disqualified_tracks: list[str] = Field(default_factory=list)


class RunMeta(BaseModel):
    schema_version: int = 1
    run_id: str
    repo_path: str
    mode: Literal["debug", "harden"]
    issue_text_present: bool = False
    use_docker: bool = False
    use_treesitter: bool = False
    tracks: list[dict[str, Any]] = Field(default_factory=list)


class FilesIndex(BaseModel):
    schema_version: int = 1
    files: list[dict[str, Any]] = Field(default_factory=list)


class IterationEnvelope(BaseModel):
    schema_version: int = 1
    track: str
    iteration: int
    status_signal: Literal["CONTINUE", "SKIP_TO_VERIFY", "READY_FOR_FIX", "NEEDS_MORE_WORK"]
    hypothesis: str
    confidence: float = 0.0
    experiments: list[dict[str, Any]] = Field(default_factory=list)
    proposed_changes: dict[str, Any] = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)


class CheckResult(BaseModel):
    schema_version: int = 1
    name: str
    ok: bool
    exit_code: int
    details: str = ""
    required_artifacts: list[str] = Field(default_factory=list)
    missing_artifacts: list[str] = Field(default_factory=list)


class JudgeDecision(BaseModel):
    schema_version: int = 1
    winner: str | None = None
    reason: str
    scores: dict[str, float] = Field(default_factory=dict)
    disqualified: list[str] = Field(default_factory=list)
