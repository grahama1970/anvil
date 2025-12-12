from __future__ import annotations

"""Artifact schemas.

CONTRACT
- Inputs: Pydantic models
- Outputs:
  - Validated JSON-serializable objects
- Invariants:
  - Defines the shape of all core artifacts (RUN.json, ITERATION.json, etc.)
  - All schemas have schema_version int field
- Failure:
  - Raises ValidationError on schema mismatch
"""

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
    issue_text: str | None = None  # Full issue text for resume support
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
    status_signal: Literal["CONTINUE", "SKIP_TO_VERIFY", "READY_FOR_FIX", "NEEDS_MORE_WORK", "DONE"]
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


def validate_iteration_json(data: dict[str, Any]) -> tuple[bool, IterationEnvelope | None, str]:
    """Validate ITERATION.json against schema.
    
    Returns: (is_valid, parsed_envelope, error_message)
    """
    try:
        envelope = IterationEnvelope(**data)
        return True, envelope, ""
    except Exception as e:
        return False, None, str(e)


def validate_run_status(data: dict[str, Any]) -> tuple[bool, RunStatus | None, str]:
    """Validate RUN_STATUS.json against schema."""
    try:
        status = RunStatus(**data)
        return True, status, ""
    except Exception as e:
        return False, None, str(e)

