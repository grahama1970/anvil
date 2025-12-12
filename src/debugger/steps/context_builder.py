"""Context builder.

CONTRACT
- Inputs:
  - repo: git repo root
  - issue text (store RUN.json has issue_text_present)
- Outputs (required):
  - CONTEXT.md
  - FILES.json (schema_version=1, files[])
- Outputs (optional):
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
            # Task 4.4: Improve keyword extraction
            # - Lower min length to 2
            # - Allow hyphens inside words
            # regex: start with word char, followed by 1+ word/hyphen chars
            words = [
                w.lower()
                for w in re.findall(r"\b[A-Za-z_][A-Za-z0-9_-]+\b", issue_text)
                if len(w) >= 2
            ][:20]  # increased limit slightly
            
            # Simple frequency filter could go here, but unique sorted is a start
            query = "|".join(sorted(set(words))) if words else "TODO"
            
            # Task 4.5: Safety - ignore generated dirs
            cmd = f'rg -n --hidden --glob "!.git/*" --glob "!.dbg/*" --glob "!__pycache__/*" "{query}" .'
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
                files = []
                for line in out.splitlines():
                    if ":" in line:
                        path_str = line.split(":", 1)[0]
                        if not path_str or path_str in files:
                            continue
                            
                        # Task 4.5: Safety checks (size, binary)
                        fp = repo / path_str
                        try:
                            stats = fp.stat()
                            if stats.st_size > 1_000_000:  # 1MB cap
                                continue
                            # check binary content (null bytes in first chunk)
                            with fp.open("rb") as f:
                                chunk = f.read(1024)
                                if b"\0" in chunk:
                                    continue
                        except Exception:
                            continue
                            
                        files.append(path_str)
                        
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
        return 0 if res.ok else 1

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Context Builder Step")
    parser.add_argument("--repo", required=True, help="Path to repo")
    parser.add_argument("--issue", required=True, help="Issue text")
    parser.add_argument("--out-dir", required=True, help="Output directory for artifacts")
    parser.add_argument("--treesitter", action="store_true", help="Enable tree-sitter")
    args = parser.parse_args()

    try:
        store = ArtifactStore(Path(args.out_dir))
        step = ContextBuilder()
        step.run(
            store,
            Path(args.repo),
            args.issue,
            use_treesitter=args.treesitter,
            max_files=50,
        )
        sys.exit(step.check(store, Path(args.repo)))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
