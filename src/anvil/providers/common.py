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

from ..util.json_utils import parse_json

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
    """Ensure iteration JSON matches schema minimal requirements.
    
    Uses json_repair library to handle malformed LLM output (control chars,
    trailing commas, unquoted keys, etc).
    """
    # Use robust parse_json which applies json_repair
    data = parse_json(raw_json)
    
    # If parse_json failed completely, return fallback
    if not isinstance(data, dict):
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
    
    # Role-aware patch requirements
    is_fixer_role = role.lower() in ("fixer", "debugger", "backend_fixer", "frontend_fixer")
    
    if is_fixer_role:
        role_intro = "You are a contract-driven debugging agent. Your job is to FIX BUGS by producing code patches.\n"
        patch_instruction = (
            "CRITICAL: You MUST produce a unified diff patch to fix the issue. Do NOT say NO_PATCH.\n"
            "If the issue description asks for code changes, you MUST provide them.\n"
        )
    else:
        # Breaker, explorer, or other analysis roles
        role_intro = f"You are a {role} agent. Your job is to analyze code for issues, vulnerabilities, or improvements.\n"
        patch_instruction = (
            "If you find an issue, you are ENCOURAGED to produce a unified diff patch that either:\n"
            "1. Adds a test case that exposes the issue, OR\n"
            "2. Fixes the vulnerability/bug directly.\n"
            "A patch is optional but strongly preferred when you have high confidence.\n"
        )
    
    return (
        role_intro +
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
        "\n" +
        patch_instruction +
        "\n"
        "Return EXACTLY the following markers and contents:\n"
        f"{_BEGIN_JSON}\n"
        "JSON must be a single object matching this shape (use status_signal DONE when proposing a fix):\n"
        f"{json.dumps(schema_hint, indent=2)}\n"
        f"{_END_JSON}\n"
        f"{_BEGIN_DIFF}\n"
        "A complete unified diff (git diff format) that fixes the issue.\n"
        "Example format:\n"
        "--- a/path/to/file.py\n"
        "+++ b/path/to/file.py\n"
        "@@ -10,5 +10,7 @@\n"
        " existing line\n"
        "-old line to remove\n"
        "+new line to add\n"
        f"{_END_DIFF}\n"
    )
