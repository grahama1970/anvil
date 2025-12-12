import pytest
from pathlib import Path
from src.anvil.artifacts.store import ArtifactStore

def test_store_path_ok(tmp_path):
    store = ArtifactStore(tmp_path / "runs")
    # Setup a run dir
    # ArtifactStore usually needs run_id or assumes current run?
    # Let's check ArtifactStore contract. 
    # It takes a root, but .path() joins arguments relative to run_dir? 
    # Actually ArtifactStore takes 'root', run_dir is property?
    # Wait, ArtifactStore(path) sets self.run_dir = path usually in this codebase context?
    # Let me check ArtifactStore definition quickly if implementation differs or assumes it IS the run dir.
    # Based on usage `store = ArtifactStore(Path(args.out_dir))`, the passed path IS the run dir.
    
    p = store.path("subdir", "file.txt")
    assert p == tmp_path / "runs" / "subdir" / "file.txt"

def test_store_path_traversal(tmp_path):
    store = ArtifactStore(tmp_path / "runs")
    
    # Simple traversal
    with pytest.raises(ValueError, match="Refusing to access path"):
        store.path("..", "secret.txt")
        
    # Nested traversal
    with pytest.raises(ValueError, match="Refusing to access path"):
        store.path("subdir", "../../secret.txt")

def test_store_ensure(tmp_path):
    store = ArtifactStore(tmp_path / "runs")
    assert not (tmp_path / "runs").exists()
    store.ensure()
    assert (tmp_path / "runs").exists()

def test_store_write_json(tmp_path):
    store = ArtifactStore(tmp_path / "runs")
    store.ensure()
    store.write_json("foo.json", {"a": 1})
    assert (tmp_path / "runs" / "foo.json").read_text().strip() == '{\n  "a": 1\n}'.strip()
