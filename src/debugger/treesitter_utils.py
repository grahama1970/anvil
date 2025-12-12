"""Tree-sitter utilities (optional).

CONTRACT
- Inputs: File path
- Outputs (optional):
  - List of symbol dictionaries (kind, name, start_line, end_line)
- Invariants:
  - If tree-sitter deps missing, returns empty list (no crash)
  - Supports .py, .js, .ts, .tsx, .jsx
- Failure:
  - Returns empty list on any parse error or missing dependency
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_EXT = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
}


@dataclass(frozen=True)
class Symbol:
    kind: str
    name: str
    start_line: int
    end_line: int


def _try_import_treesitter_tools():
    try:
        from treesitter_tools.api import list_symbols  # type: ignore

        return list_symbols
    except Exception:
        return None


def _try_import_tree_sitter_languages():
    try:
        from tree_sitter_languages import get_parser  # type: ignore

        return get_parser
    except Exception:
        return None


def outline_symbols(path: Path) -> list[dict[str, Any]]:
    list_symbols = _try_import_treesitter_tools()
    if list_symbols is not None:
        try:
            symbols = list_symbols(path)
        except Exception:
            symbols = None
        if symbols is not None:
            out: list[dict[str, Any]] = []
            for s in symbols:
                out.append(
                    {
                        "kind": getattr(s, "kind", ""),
                        "name": getattr(s, "name", ""),
                        "start_line": int(getattr(s, "start_line", 0) or 0),
                        "end_line": int(getattr(s, "end_line", 0) or 0),
                    }
                )
            return out

    get_parser = _try_import_tree_sitter_languages()
    if get_parser is None:
        return []

    lang_name = SUPPORTED_EXT.get(path.suffix.lower())
    if not lang_name:
        return []

    try:
        parser = get_parser(lang_name)
    except Exception:
        return []

    try:
        src = path.read_bytes()
    except Exception:
        return []

    tree = parser.parse(src)
    root = tree.root_node

    symbols: list[Symbol] = []

    def text_for(node) -> str:
        return src[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")

    # Very small, pragmatic queries; refine per-language later.
    # We avoid Query objects to keep this simple and robust.
    stack = [root]
    while stack:
        node = stack.pop()
        t = getattr(node, "type", "")
        if lang_name == "python":
            if t in ("function_definition", "class_definition"):
                name_node = None
                for ch in node.children:
                    if ch.type == "identifier":
                        name_node = ch
                        break
                if name_node is not None:
                    symbols.append(
                        Symbol(
                            kind="function" if t == "function_definition" else "class",
                            name=text_for(name_node),
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                        )
                    )
        else:
            if t in ("function_declaration", "class_declaration", "method_definition"):
                # best-effort identifier lookup
                name_node = None
                for ch in node.children:
                    if ch.type in ("identifier", "property_identifier"):
                        name_node = ch
                        break
                if name_node is not None:
                    symbols.append(
                        Symbol(
                            kind="function" if "function" in t or "method" in t else "class",
                            name=text_for(name_node),
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                        )
                    )
        for ch in getattr(node, "children", []):
            stack.append(ch)

    return [s.__dict__ for s in symbols]


if __name__ == "__main__":
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Tree-sitter Utils CLI")
    parser.add_argument("--file", required=True, help="Path to file")
    args = parser.parse_args()

    try:
        symbols = outline_symbols(Path(args.file))
        print(json.dumps(symbols, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
