import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "harvest.py"


def test_harvest_script_exists_and_is_loadable():
    assert SCRIPTS.is_file()
    spec = importlib.util.spec_from_file_location("harvest", SCRIPTS)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert module


def test_harvest_module_has_main():
    spec = importlib.util.spec_from_file_location("harvest", SCRIPTS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "main")
