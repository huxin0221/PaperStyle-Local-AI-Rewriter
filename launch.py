"""Launch using the virtual environment next to this file."""
import os
import sys
from pathlib import Path


def main():
    project = Path(__file__).resolve().parent
    environment = project / '.venv'
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if python.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        os.execv(str(python), [str(python), str(project / 'launch.py')] + sys.argv[1:])
    if sys.version_info[:2] != (3, 11):
        raise SystemExit('This UI build requires Python 3.11. Select ScholarStyle_Studio/.venv '
                         'as the PyCharm interpreter, or use start.command / start.bat.')
    from scholarstyle.gui import main as run_gui
    run_gui()


if __name__ == '__main__':
    main()
