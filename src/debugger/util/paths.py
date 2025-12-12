from __future__ import annotations

import importlib.resources
import re
from pathlib import Path

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def copy_template(template_name: str, dest: Path) -> None:
    # Only write if missing (avoid clobber).
    if dest.exists():
        return
    pkg = "debugger.templates"
    with importlib.resources.open_text(pkg, template_name, encoding="utf-8") as f:
        dest.write_text(f.read(), encoding="utf-8")


def safe_filename(name: str, *, default: str = "item") -> str:
    cleaned = _SAFE_FILENAME_RE.sub("_", name).strip("._-")
    return cleaned or default
