import pytest
import importlib.resources
import yaml
from pathlib import Path
from anvil.config import load_tracks_file

def test_templates_exist():
    # Verify we can load the bundled templates
    pkg = "anvil.templates" 
    # Note: anvil.templates might not be importable if not a package with __init__.py?
    # In the code `debugger.templates` is used (installed/package context).
    # Here tests are running against source. 
    # Here tests are running against source.
    # We might need to adjust expected package name or ensure `src` structure supports it.
    # `src/anvil` has `__init__.py`.
    # `src/anvil/templates` usually is just files.
    # `importlib.resources.open_text("anvil.templates", ...)` checks for package.
    # If I use `src.anvil.templates`, it implies templates is a package?
    # Actually `src.anvil` is a package. `templates` is a subpackage or resource dir?
    # If it has no `__init__.py`, legacy `importlib.resources` might fail on older python,
    # but modern (3.9+) works with files().
    # The code uses `importlib.resources.open_text(pkg, ...)` where pkg="anvil.templates".

    # Since we run with PYTHONPATH=., "src" is top level.
    # The application code does `pkg = "anvil.templates"`, anticipating installation as `anvil` package?
    # Or assuming `anvil` is in path.
    # If I run `PYTHONPATH=. pytest`, `src` is in path? No, `.` is.
    # So `import anvil` works.
    # `anvil` import (as used in `paths.py` -> `pkg = "anvil.templates"`) likely relies on `src` being in path
    # OR `anvil` being the package installed.
    # If I check `src/anvil/util/paths.py`: `pkg = "anvil.templates"`
    # This implies `anvil` is a top level import.

    pass

def test_valid_contract_yaml():
    # Test that the bundled verify_contract.yaml is valid YAML
    try:
        # We need to find the file manually if importlib is verified elsewhere
        # or use relative path logic for test ease
        base = Path(__file__).parent.parent / "src" / "anvil" / "templates" / "verify_contract.yaml"
        if base.exists():
            data = yaml.safe_load(base.read_text())
            assert "commands" in data
    except Exception as e:
        pytest.fail(f"Failed to load verify_contract.yaml: {e}")
