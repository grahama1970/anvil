from __future__ import annotations

"""Contract validation utilities.

CONTRACT
- Inputs: Run directory, list of required artifact names
- Outputs (required):
  - CheckResult (ok=bool, exit_code=int)
- Invariants:
  - Checks existence of all required files
- Failure:
  - Returns CheckResult(ok=False, exit_code=2) if any missing
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ..artifacts.schemas import CheckResult


@dataclass(frozen=True)
class ContractViolation(Exception):
    message: str


def check_required_artifacts(run_dir: Path, required: Sequence[str]) -> CheckResult:
    missing = [r for r in required if not (run_dir / r).exists()]
    ok = len(missing) == 0
    exit_code = 0 if ok else 2
    return CheckResult(
        name="required_artifacts",
        ok=ok,
        exit_code=exit_code,
        details="OK" if ok else "Missing required artifacts",
        required_artifacts=list(required),
        missing_artifacts=missing,
    )
