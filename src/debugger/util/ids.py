from __future__ import annotations

import datetime
import random
import re
import string

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_TRACK_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")


def new_run_id() -> str:
    # YYYYMMDD_HHMMSS_<rand4>
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
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
