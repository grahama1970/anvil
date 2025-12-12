from __future__ import annotations

"""Path utilities.

CONTRACT
- Inputs: strings (filenames) or paths
- Outputs:
  - safe_filename() returns sanitized string (no path separators)
  - ensure_dir() creates directory tree
  - copy_template() writes bundled resource to dest
- Invariants:
  - safe_filename removes dangerous chars `[^A-Za-z0-9_.-]`
  - copy_template never overwrites existing files (unless `overwrite=True`)
- Failure:
  - copy_template raises if resource missing
"""

import importlib.resources
import re
from pathlib import Path

from .. import templates

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def copy_template(template_name: str, dest: Path, overwrite: bool = False) -> None:
    # Only write if missing (avoid clobber) unless forced.
    if dest.exists() and not overwrite:
        return
    with importlib.resources.open_text(templates, template_name, encoding="utf-8") as f:
        dest.write_text(f.read(), encoding="utf-8")


def safe_filename(name: str, *, default: str = "item") -> str:
    cleaned = _SAFE_FILENAME_RE.sub("_", name).strip("._-")
    return cleaned or default

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Path utilities")
    parser.add_argument("--safe-filename", help="Sanitize a filename")
    args = parser.parse_args()

    if args.safe_filename:
        print(safe_filename(args.safe_filename))
    else:
        parser.print_help()
        sys.exit(1)
