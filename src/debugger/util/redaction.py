from __future__ import annotations

import re
from dataclasses import dataclass, field

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
