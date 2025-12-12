from __future__ import annotations

"""ID generation and validation.

CONTRACT
- Inputs: Run IDs, Track names
- Outputs (required):
  - new_run_id() returns time-sortable string
  - validate_run_id() returns validated ID or raises
- Invariants:
  - Run IDs match `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`
  - Track names match `[A-Za-z0-9][A-Za-z0-9_-]{0,31}`
- Failure:
  - Raises ValueError on invalid IDs
"""

import datetime
import random
import re
import string

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_TRACK_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")


def new_run_id() -> str:
    # YYYYMMDD_HHMMSS_<rand4>
    ts = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    suffix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(4))
    return f"{ts}_{suffix}"


def validate_run_id(run_id: str) -> str:
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError(
            "Invalid run id. Use 1-64 chars: letters/digits, plus '._-'. Must start with a letter "
            "or digit."
        )
    return run_id


def validate_track_name(name: str) -> str:
    if not _TRACK_NAME_RE.fullmatch(name):
        raise ValueError(
            "Invalid track name. Use 1-32 chars: letters/digits, plus '_-'. Must start with a "
            "letter or digit."
        )
    return name

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Utilities for run IDs and track names")
    parser.add_argument("--new-run-id", action="store_true", help="Generate a new run ID")
    parser.add_argument("--validate-run-id", help="Validate a run ID (returns it or fails)")
    parser.add_argument("--validate-track", help="Validate a track name (returns it or fails)")
    args = parser.parse_args()

    try:
        if args.new_run_id:
            print(new_run_id())
        elif args.validate_run_id:
            print(validate_run_id(args.validate_run_id))
        elif args.validate_track:
            print(validate_track_name(args.validate_track))
        else:
            parser.print_help()
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
