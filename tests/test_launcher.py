import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import importlib.util
import pytest


def launcher():
    spec = importlib.util.spec_from_file_location('studio_launcher', Path(__file__).parents[1] / 'launch.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launch_uses_project_environment(monkeypatch):
    module = launcher()
    monkeypatch.setattr(module.sys, 'prefix', '/different/environment')
    def execute(executable, args):
        assert executable.endswith('/ScholarStyle_Studio/.venv/bin/python')
        assert Path(args[1]).name == 'launch.py'
        raise SystemExit(0)
    monkeypatch.setattr(module.os, 'execv', execute)
    with pytest.raises(SystemExit) as result:
        module.main()
    assert result.value.code == 0


def test_launch_calls_gui_in_correct_environment(monkeypatch):
    module = launcher()
    monkeypatch.setattr(module.sys, 'prefix', str(Path(module.__file__).parent / '.venv'))
    monkeypatch.setattr(module.sys, 'version_info', (3, 11))
    gui = SimpleNamespace(main=Mock())
    monkeypatch.setitem(sys.modules, 'scholarstyle.gui', gui)
    module.main()
    gui.main.assert_called_once_with()


def test_incompatible_environment_has_actionable_error(monkeypatch):
    module = launcher()
    monkeypatch.setattr(module.sys, 'prefix', str(Path(module.__file__).parent / '.venv'))
    monkeypatch.setattr(module.sys, 'version_info', (3, 10))
    with pytest.raises(SystemExit, match='requires Python 3.11'):
        module.main()
