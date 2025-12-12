from __future__ import annotations

import importlib.resources


def load_profile(name: str) -> str:
    pkg = "debugger.prompts.profiles"
    fname = f"{name}.md"
    with importlib.resources.open_text(pkg, fname, encoding="utf-8") as f:
        return f.read()
