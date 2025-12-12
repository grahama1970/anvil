from __future__ import annotations

"""Text IO utilities.

CONTRACT
- Inputs: Path
- Outputs:
  - File content as string
- Invariants:
  - Reads as utf-8
- Failure:
  - Raises FileNotFoundError/IOError
"""

from pathlib import Path


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")
