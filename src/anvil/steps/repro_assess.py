"""Reproduction assessment step.

CONTRACT
- Inputs: Repo path, issue text
- Outputs (required):
  - REPRO_ASSESS.json (repro_mode, strategy, commands)
- Invariants:
  - Determines reproduction mode: AUTO, SEMI_AUTO, MANUAL
  - Checks for existing test files, repro scripts, etc.
- Failure:
  - Defaults to MANUAL if assessment fails
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ..artifacts.store import ArtifactStore


class ReproMode(str, Enum):
    """Reproduction mode for debugging."""
    AUTO = "AUTO"           # Bug reproducible via automated tests/scripts
    SEMI_AUTO = "SEMI_AUTO" # Needs manual setup, then automated verification
    MANUAL = "MANUAL"       # Requires manual user reproduction


@dataclass
class ReproAssessment:
    """Result of reproduction assessment."""
    mode: ReproMode
    strategy: str
    commands: list[str]
    confidence: float
    details: str


@dataclass
class ReproAssess:
    """Assess how a bug can be reproduced."""
    
    name: str = "repro_assess"
    
    def run(self, store: ArtifactStore, repo: Path, issue_text: str | None = None) -> ReproAssessment:
        """Analyze repo to determine reproduction strategy.
        
        Returns ReproAssessment with mode, strategy, and suggested commands.
        """
        commands: list[str] = []
        confidence = 0.0
        details_parts: list[str] = []
        
        # Check for test infrastructure
        has_pytest = (repo / "pyproject.toml").exists() or (repo / "setup.py").exists()
        has_npm = (repo / "package.json").exists()
        has_makefile = (repo / "Makefile").exists()
        
        # Check for repro scripts
        repro_scripts = list(repo.glob("**/repro*.sh")) + list(repo.glob("**/reproduce*.sh"))
        debug_scripts = list(repo.glob("**/debug*.sh"))
        
        # Check for test directories
        test_dirs = list(repo.glob("tests/")) + list(repo.glob("test/")) + list(repo.glob("**/test_*.py"))
        
        # Determine mode based on available infrastructure
        if repro_scripts:
            # Has explicit repro script - AUTO
            mode = ReproMode.AUTO
            commands = [f"./{repro_scripts[0].relative_to(repo)}"]
            confidence = 0.9
            details_parts.append(f"Found repro script: {repro_scripts[0].name}")
        
        elif test_dirs and has_pytest:
            # Has pytest infrastructure - AUTO
            mode = ReproMode.AUTO
            commands = ["uv run pytest -q", "uv run pytest -v --tb=short"]
            confidence = 0.8
            details_parts.append("Found pytest test infrastructure")
            
            # Check if issue mentions specific test
            if issue_text and "test_" in issue_text.lower():
                # Try to extract test name
                import re
                test_match = re.search(r'test_\w+', issue_text, re.IGNORECASE)
                if test_match:
                    commands.insert(0, f"uv run pytest -v -k '{test_match.group()}'")
                    details_parts.append(f"Issue mentions test: {test_match.group()}")
        
        elif has_npm:
            # Has npm - check for test script
            try:
                pkg = json.loads((repo / "package.json").read_text())
                if "test" in pkg.get("scripts", {}):
                    mode = ReproMode.AUTO
                    commands = ["npm test"]
                    confidence = 0.7
                    details_parts.append("Found npm test script")
                else:
                    mode = ReproMode.SEMI_AUTO
                    commands = ["npm run dev"]
                    confidence = 0.4
                    details_parts.append("Has package.json but no test script")
            except Exception:
                mode = ReproMode.SEMI_AUTO
                commands = ["npm run dev"]
                confidence = 0.3
                details_parts.append("Could not parse package.json")
        
        elif has_makefile:
            # Has Makefile - check for test target
            try:
                makefile = (repo / "Makefile").read_text()
                if "test:" in makefile or "check:" in makefile:
                    mode = ReproMode.AUTO
                    commands = ["make test"]
                    confidence = 0.6
                    details_parts.append("Found Makefile with test target")
                else:
                    mode = ReproMode.SEMI_AUTO
                    confidence = 0.3
                    details_parts.append("Makefile found but no test target")
            except Exception:
                mode = ReproMode.SEMI_AUTO
                confidence = 0.2
                details_parts.append("Could not read Makefile")
        
        else:
            # No obvious automation - MANUAL
            mode = ReproMode.MANUAL
            confidence = 0.1
            details_parts.append("No automated test infrastructure found")
        
        # Build strategy description
        if mode == ReproMode.AUTO:
            strategy = f"Run automated tests: {', '.join(commands)}"
        elif mode == ReproMode.SEMI_AUTO:
            strategy = "Manual setup required, then verify with commands"
        else:
            strategy = "Manual reproduction required - follow issue steps"
        
        assessment = ReproAssessment(
            mode=mode,
            strategy=strategy,
            commands=commands,
            confidence=confidence,
            details="; ".join(details_parts),
        )
        
        # Write assessment artifact
        artifact: dict[str, Any] = {
            "schema_version": 1,
            "repro_mode": mode.value,
            "strategy": strategy,
            "commands": commands,
            "confidence": confidence,
            "details": assessment.details,
        }
        store.write_json("REPRO_ASSESS.json", artifact)
        
        # Write human-readable version
        md = [
            "# Reproduction Assessment",
            "",
            f"**Mode**: {mode.value}",
            f"**Confidence**: {confidence:.0%}",
            "",
            "## Strategy",
            strategy,
            "",
            "## Commands",
        ]
        for cmd in commands:
            md.append(f"```bash\n{cmd}\n```")
        md += ["", "## Details", assessment.details]
        store.write_text("REPRO_ASSESS.md", "\n".join(md))
        
        return assessment
    
    def check(self, store: ArtifactStore) -> int:
        """Verify REPRO_ASSESS.json was written."""
        p = store.path("REPRO_ASSESS.json")
        if not p.exists():
            return 2
        try:
            data = json.loads(p.read_text())
            if "repro_mode" not in data:
                return 2
            return 0
        except Exception:
            return 2


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Reproduction Assessment")
    parser.add_argument("--repo", required=True, help="Path to repo")
    parser.add_argument("--issue", default="", help="Issue text")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    args = parser.parse_args()

    try:
        store = ArtifactStore(Path(args.out_dir))
        step = ReproAssess()
        result = step.run(store, Path(args.repo), args.issue)
        print(f"Repro Mode: {result.mode.value}")
        print(f"Strategy: {result.strategy}")
        print(f"Commands: {result.commands}")
        sys.exit(step.check(store))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
