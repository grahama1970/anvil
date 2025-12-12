import pytest
import json
from anvil.providers.common import extract_between, normalize_iteration_json, build_prompt
from anvil.providers.base import ProviderResult

def test_extract_between():
    text = "ignore START content END ignore"
    assert extract_between(text, "START", "END") == "content"
    
    # Missing end
    assert extract_between(text, "START", "MISSING") == ""
    
    # Missing start
    assert extract_between(text, "MISSING", "END") == ""
    
    # Nested/Repeated (contract: find last start?) 
    # Let's check implementation behavior or contract.
    # common.py says: "Find last start marker"
    text2 = "START first END ... START second END"
    # If it finds last START "START second END", then scans forward for END.
    # It should extract "second".
    assert extract_between(text2, "START", "END") == "second"

def test_normalize_iteration_json():
    # Minimal input
    raw = {}
    normalized = json.loads(normalize_iteration_json(json.dumps(raw)))
    assert normalized["schema_version"] == 1
    assert normalized["status_signal"] == "NEEDS_MORE_WORK"
    
    # Malformed input
    bad_json = "{ bad json"
    normalized_bad = json.loads(normalize_iteration_json(bad_json))
    assert normalized_bad["thought"] == "Failed to parse JSON"
    assert normalized_bad["confidence"] == 0.0

def test_build_prompt():
    prompt = build_prompt(
        track="track1",
        iteration=1,
        role="debugger",
        directions="Do X",
        context="CTX",
        blackboard="BB"
    )
    assert "ROLE: debugger" in prompt
    assert "DIRECTIONS:\nDo X" in prompt
    assert "CTX" in prompt
    assert "BEGIN_ITERATION_JSON" in prompt
