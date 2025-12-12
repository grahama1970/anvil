import pytest
import importlib.resources
import yaml
from pathlib import Path
from src.debugger.config import load_tracks_file

def test_templates_exist():
    # Verify we can load the bundled templates
    pkg = "src.debugger.templates" 
    # Note: src.debugger.templates might not be importable if not a package with __init__.py?
    # In the code `debugger.templates` is used (installed/package context).
    # Here tests are running against source. 
    # We might need to adjust expected package name or ensure `src` structure supports it.
    # `src/debugger` has `__init__.py`. 
    # `src/debugger/templates` usually is just files.
    # `importlib.resources.open_text("debugger.templates", ...)` checks for package.
    # If I use `src.debugger.templates`, it implies templates is a package?
    # Actually `src.debugger` is a package. `templates` is a subpackage or resource dir?
    # If it has no `__init__.py`, legacy `importlib.resources` might fail on older python, 
    # but modern (3.9+) works with files().
    # The code uses `importlib.resources.open_text(pkg, ...)` where pkg="debugger.templates".
    
    # Since we run with PYTHONPATH=., "src" is top level.
    # The application code does `pkg = "debugger.templates"`, anticipating installation as `debugger` package?
    # Or assuming `debugger` is in path.
    # If I run `PYTHONPATH=. pytest`, `src` is in path? No, `.` is.
    # So `import src.debugger` works.
    # `debugger` import (as used in `paths.py` -> `pkg = "debugger.templates"`) likely relies on `src` being in path 
    # OR `debugger` being the package installed.
    # If I check `src/debugger/util/paths.py`: `pkg = "debugger.templates"`
    # This implies `debugger` is a top level import.
    # So I probably need `PYTHONPATH=src`.
    
    pass

def test_valid_contract_yaml():
    # Test that the bundled verify_contract.yaml is valid YAML
    try:
        # We need to find the file manually if importlib is verified elsewhere
        # or use relative path logic for test ease
        base = Path(__file__).parent.parent / "src" / "debugger" / "templates" / "verify_contract.yaml"
        if base.exists():
            data = yaml.safe_load(base.read_text())
            assert "commands" in data
    except Exception as e:
        pytest.fail(f"Failed to load verify_contract.yaml: {e}")
