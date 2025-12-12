import pytest
from pathlib import Path
from src.anvil.util.paths import safe_filename, ensure_dir, copy_template

def test_safe_filename():
    assert safe_filename("foo") == "foo"
    assert safe_filename("foo bar") == "foo_bar"
    assert safe_filename("foo/bar") == "foo_bar"
    assert safe_filename("../../etc/passwd") == "etc_passwd"
    assert safe_filename("") == "item"  # Default
    assert safe_filename("", default="default") == "default"

def test_ensure_dir(tmp_path):
    d = tmp_path / "subdir" / "nested"
    assert not d.exists()
    ensure_dir(d)
    assert d.exists()
    assert d.is_dir()

def test_copy_template(tmp_path, monkeypatch):
    # Mock importlib.resources to avoid needing real template files
    import importlib.resources
    from contextlib import contextmanager
    
    # Mock context manager for open_text
    @contextmanager
    def mock_open_text(pkg, name, encoding="utf-8"):
        class MockFile:
            def read(self):
                return f"Template content for {name}"
        yield MockFile()

    monkeypatch.setattr(importlib.resources, "open_text", mock_open_text)

    dest = tmp_path / "template.txt"
    
    # First write
    copy_template("some_template", dest)
    assert dest.read_text(encoding="utf-8") == "Template content for some_template"

    # Second write (no overwrite)
    dest.write_text("Modified", encoding="utf-8")
    copy_template("some_template", dest)
    assert dest.read_text(encoding="utf-8") == "Modified"

    # Force overwrite
    copy_template("some_template", dest, overwrite=True)
    assert dest.read_text(encoding="utf-8") == "Template content for some_template"
