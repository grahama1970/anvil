import pytest
import uuid
from anvil.util.ids import validate_run_id, validate_track_name, new_run_id

def test_validate_run_id_valid():
    # Valid UUIDs
    uid = str(uuid.uuid4())
    assert validate_run_id(uid) == uid
    
    # Valid nice-name IDs (if supported, checking implementation)
    # The implementation supports UUID hex (32 chars) or UUID string (36 chars) usually?
    # Let's check implementation behavior via test.
    # Actually validate_run_id usually enforces UUID format.
    pass

def test_validate_run_id_invalid():
    with pytest.raises(ValueError, match="Invalid run id"):
        validate_run_id("invalid/id")
    with pytest.raises(ValueError, match="Invalid run id"):
        validate_run_id("invalid id")
    with pytest.raises(ValueError):
        validate_run_id("")

def test_new_run_id():
    rid = new_run_id()
    assert validate_run_id(rid) == rid

def test_validate_track_name_valid():
    assert validate_track_name("valid_name") == "valid_name"
    assert validate_track_name("Valid-Name-123") == "Valid-Name-123"
    assert validate_track_name("a") == "a"
    # Max length 32
    long_name = "a" * 32
    assert validate_track_name(long_name) == long_name

def test_validate_track_name_invalid():
    # Too long
    with pytest.raises(ValueError):
        validate_track_name("a" * 33)
    # Invalid chars
    with pytest.raises(ValueError):
        validate_track_name("invalid name")
    with pytest.raises(ValueError):
        validate_track_name("invalid/name")
    with pytest.raises(ValueError):
        validate_track_name(".starts_with_period")
    # Empty
    with pytest.raises(ValueError):
        validate_track_name("")
