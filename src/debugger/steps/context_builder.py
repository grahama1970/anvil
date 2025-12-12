"""Context builder.

CONTRACT
- Inputs:
  - repo: git repo root
  - issue text (store RUN.json has issue_text_present)
- Outputs (required):
  - CONTEXT.md
  - FILES.json (schema_version=1, files[])
- Optional outputs:
  - SYMBOLS.json (if tree-sitter enabled and available)
- Invariants:
  - FILES.json paths are repo-relative
  - CONTEXT.md references only files listed in FILES.json (best-effort)
- Failure:
  - check() returns 2 if required artifacts missing/invalid
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..artifacts.schemas import FilesIndex
from ..artifacts.store import ArtifactStore
from ..contracts.validate import check_required_artifacts
from ..treesitter_utils import outline_symbols
from ..util.shell import run_cmd, which


@dataclass
class ContextBuilder:
    name: str = "context_builder"

    def run(
        self,
        store: ArtifactStore,
        repo: Path,
        issue_text: str,
        use_treesitter: bool,
        max_files: int,
    ) -> None:
        store.ensure()
        rg = which("rg")
        candidates: list[dict[str, Any]] = []

        if rg:
            # Extract a few keywords from issue text (very simple).
            words = [w.lower() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", issue_text)][:12]
            query = "|".join(sorted(set(words))) if words else "TODO"
            cmd = f'rg -n --hidden --glob "!.git/*" "{query}" .'
            res = run_cmd(
                cmd=cmd,
                cwd=repo,
                stdout_path=store.path("logs", "context_rg.stdout.log"),
                stderr_path=store.path("logs", "context_rg.stderr.log"),
                timeout_s=30,
            )
            if res.returncode == 0:
                out = store.path("logs", "context_rg.stdout.log").read_text(
                    encoding="utf-8", errors="ignore"
                )
                # Parse file paths from ripgrep output "path:line:match"
                files = []
                for line in out.splitlines():
                    if ":" in line:
                        path = line.split(":", 1)[0]
                        if path and path not in files:
                            files.append(path)
                    if len(files) >= max_files:
                        break
                candidates = [{"path": p, "rationale": "keyword hit"} for p in files]
        else:
            # Fallback: include a few common files if present
            for p in ["README.md", "pyproject.toml", "package.json"]:
                if (repo / p).exists():
                    candidates.append({"path": p, "rationale": "fallback"})
            candidates = candidates[:max_files]

        files_index = FilesIndex(files=candidates)
        store.write_json("FILES.json", files_index.model_dump())

        context_md = [
            "# CONTEXT",
            "",
            "## Issue",
            "```text",
            issue_text.strip(),
            "```",
            "",
            "## Selected files (FILES.json)",
        ]
        for c in candidates:
            context_md.append(f"- `{c['path']}` — {c.get('rationale', '')}")
        context_md.append("")
        store.write_text("CONTEXT.md", "\n".join(context_md) + "\n")

        if use_treesitter:
            symbols: dict[str, Any] = {"schema_version": 1, "symbols": []}
            for c in candidates:
                fp = repo / c["path"]
                if fp.exists() and fp.is_file():
                    outline = outline_symbols(fp)
                    if outline:
                        symbols["symbols"].append({"path": c["path"], "outline": outline})
            store.write_json("SYMBOLS.json", symbols)

    def check(self, store: ArtifactStore, repo: Path) -> int:
        res = check_required_artifacts(store.run_dir, ["CONTEXT.md", "FILES.json"])
        store.write_json("CHECK_context_builder.json", res.model_dump())
        return res.exit_code
