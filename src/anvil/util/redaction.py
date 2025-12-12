from __future__ import annotations

"""Redaction utility.

CONTRACT
- Inputs: text strings
- Outputs:
  - redacted text string
- Invariants:
  - Replaces known secrets (GitHub tokens, OpenAI keys) with [REDACTED]
  - Best-effort; does not guarantee all secrets are caught
- Failure:
  - None (returns original text on error or no match)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATTERNS = [
    # Common token patterns (very rough; expand in consumer repos)
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]


@dataclass(frozen=True)
class Redactor:
    patterns: list[re.Pattern] = field(default_factory=lambda: list(DEFAULT_PATTERNS))

    def redact(self, text: str) -> str:
        out = text
        for pat in self.patterns:
            out = pat.sub("[REDACTED]", out)
        return out

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Redact secrets from text")
    parser.add_argument("--text", help="Text to redact")
    parser.add_argument("--file", help="File to read and redact")
    args = parser.parse_args()

    r = Redactor()
    if args.text:
        print(r.redact(args.text))
    elif args.file:
        try:
            content = Path(args.file).read_text(encoding="utf-8")
            print(r.redact(content))
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
