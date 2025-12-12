from __future__ import annotations

"""Event logging.

CONTRACT
- Inputs: Arbitrary kwargs
- Outputs:
  - Appends JSON line to configured log path
- Invariants:
  - Adds `ts_ms` timestamp automatically
  - Thread-safe (file append is atomic-ish on POSIX)
- Failure:
  - Raises IOError if log path is not writable
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class EventLog:
    path: Path
    run_id: str | None = None

    def emit(self, **event: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event.setdefault("ts_ms", int(time.time() * 1000))
        if self.run_id and "run_id" not in event:
            event["run_id"] = self.run_id
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Append JSON event to log")
    parser.add_argument("--log-path", required=True, help="Path to event log file")
    parser.add_argument("--data", required=True, help="JSON string data to emit")
    parser.add_argument("--run-id", help="Optional run_id to inject")
    args = parser.parse_args()

    try:
        data = json.loads(args.data)
        log = EventLog(Path(args.log_path), run_id=args.run_id)
        log.emit(**data)
        print(f"Emitted event to {args.log_path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
