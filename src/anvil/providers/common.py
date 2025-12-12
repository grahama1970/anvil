"""Shared provider utilities.

CONTRACT
- Inputs: Prompt components, iteration data
- Outputs: Normalized JSON strings, constructed prompts
- Invariants:
  - extract_json always returns a string (empty if failed)
  - normalize_iteration_json always returns strict JSON schema
- Failure:
  - Returns empty string or minimal valid JSON on failure
"""

import json
import re

def extract_between(text: str, start_marker: str, end_marker: str) -> str:
    """Extract text between valid markers."""
    if not text or not start_marker or not end_marker:
        return ""
    try:
        # Find last start marker to handle nested or repeated scratchpads
        start_idx = text.rfind(start_marker)
        if start_idx == -1:
            return ""
        
        start_content = start_idx + len(start_marker)
        end_idx = text.find(end_marker, start_content)
        
        if end_idx == -1:
            # If no end marker, return everything until end of string?
            # Or fail? Contract says return empty if strict.
            # But let's be robust for streamed output usually missing end.
            # For now, strict.
            return ""
            
        return text[start_content:end_idx].strip()
    except Exception:
        return ""

def normalize_iteration_json(raw_json: str) -> str:
    """Ensure iteration JSON matches schema minimal requirements."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        # Try to fix common issues or just return empty struct
        return json.dumps({
            "schema_version": 1,
            "status_signal": "NEEDS_MORE_WORK",
            "thought": "Failed to parse JSON",
            "resolution": "loose",
            "confidence": 0.0
        })
    
    # Ensure required fields
    if "thought" not in data:
        data["thought"] = "No thought provided"
    if "resolution" not in data:
        data["resolution"] = "loose"
    if "confidence" not in data:
        data["confidence"] = 0.5
    if "schema_version" not in data:
        data["schema_version"] = 1
    if "status_signal" not in data:
        data["status_signal"] = "NEEDS_MORE_WORK"
        
    return json.dumps(data, indent=2)

def build_prompt(
    *,
    track: str,
    iteration: int,
    role: str,
    directions: str,
    context: str,
    blackboard: str,
) -> str:
    """Construct the full prompt string."""
    _BEGIN_JSON = "BEGIN_ITERATION_JSON"
    _END_JSON = "END_ITERATION_JSON"
    _BEGIN_DIFF = "BEGIN_PATCH_DIFF"
    _END_DIFF = "END_PATCH_DIFF"

    schema_hint = {
        "schema_version": 1,
        "track": track,
        "iteration": iteration,
        "status_signal": "CONTINUE | SKIP_TO_VERIFY | READY_FOR_FIX | NEEDS_MORE_WORK | DONE",
        "hypothesis": "string",
        "confidence": 0.0,
        "experiments": [],
        "proposed_changes": {"has_patch": False},
        "risks": [],
    }
    return (
        "You are a contract-driven debugging agent.\n"
        "\n"
        f"ROLE: {role}\n"
        "\n"
        "DIRECTIONS:\n"
        f"{directions}\n"
        "\n"
        "BLACKBOARD (observations-only):\n"
        f"{blackboard}\n"
        "\n"
        "CONTEXT:\n"
        f"{context}\n"
        "\n"
        "Return ONLY the following markers and contents.\n"
        f"{_BEGIN_JSON}\n"
        "JSON must be a single object matching this shape:\n"
        f"{json.dumps(schema_hint, indent=2)}\n"
        f"{_END_JSON}\n"
        f"{_BEGIN_DIFF}\n"
        "Either a unified diff (git-style) OR the literal text NO_PATCH.\n"
        f"{_END_DIFF}\n"
    )
