from __future__ import annotations

"""Prompt profile loader.

CONTRACT
- Inputs: Profile name (stem of markdown file)
- Outputs (required):
  - Profile text content
- Invariants:
  - Loads from package `debugger.prompts.profiles`
- Failure:
  - Raises FileNotFoundError/ValueError if profile missing
"""

import importlib.resources


from . import profiles


def load_profile(name: str) -> str:
    fname = f"{name}.md"
    with importlib.resources.open_text(profiles, fname, encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Prompt Profile Loader CLI")
    parser.add_argument("--profile", required=True, help="Profile name")
    args = parser.parse_args()

    try:
        print(load_profile(args.profile))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
