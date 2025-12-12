from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class EventLog:
    path: Path

    def emit(self, **event: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event.setdefault("ts_ms", int(time.time() * 1000))
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
