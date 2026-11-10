"""Application palettes with native OS appearance detection for Qt 5."""
import subprocess
import sys
from pathlib import Path
from PyQt5 import QtGui as G


def system_is_dark():
    if sys.platform == 'darwin':
        try:
            result = subprocess.run(['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                                    capture_output=True, text=True, timeout=2)
            return result.returncode == 0 and result.stdout.strip().lower() == 'dark'
        except (OSError, subprocess.TimeoutExpired):
            pass
    elif sys.platform == 'win32':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
                return winreg.QueryValueEx(key, 'AppsUseLightTheme')[0] == 0
        except OSError:
            pass
    # Use an unmodified platform palette, not our own stylesheet/palette.
    return G.QGuiApplication.styleHints().property('colorScheme') == 2


def stylesheet(dark=False):
    colors = dict(bg='#111b29', fg='#e3edf8', card='#1b293c', edge='#34465e',
                  title='#edf5ff', muted='#adbed2', tab='#23344c', selected='#28657e',
                  button='#2c405b', hover='#3c5676', disabled='#223147', dim='#8494a9') if dark else dict(
                  bg='#f4f7fb', fg='#24334b', card='#ffffff', edge='#d6e0ec',
                  title='#173455', muted='#63758b', tab='#e6edf5', selected='#173455',
                  button='#e5edf6', hover='#d2e1f1', disabled='#e8edf2', dim='#7b8899')
    colors['arrow'] = (Path(__file__).parent/'assets'/'chevron.svg').as_posix()
    return '''
QMainWindow, QWidget { background:%(bg)s; color:%(fg)s; font-size:13px; }
QLabel#brand {font-size:26px; font-weight:700; color:%(title)s;}
QLabel#subtitle {color:%(muted)s;}
QToolBar {border:0; spacing:10px; padding:8px 20px;}
QTabWidget::pane {border:1px solid %(edge)s; border-radius:10px;}
QTabBar::tab {padding:12px 18px; margin-right:5px; background:%(tab)s; border-radius:7px;}
QTabBar::tab:selected {background:%(selected)s; color:#ffffff;}
QPushButton {padding:9px 12px; background:%(button)s; border:0; border-radius:7px; font-weight:600;}
QPushButton:hover {background:%(hover)s;}
QPushButton#primary {background:#117d86; color:#ffffff;}
QPushButton#primary:hover {background:#0b636b;}
QPushButton:disabled {background:%(disabled)s; color:%(dim)s;}
QLineEdit,QPlainTextEdit,QTextBrowser,QListWidget,QSpinBox,QComboBox {background:%(card)s; border:1px solid %(edge)s; border-radius:7px; padding:8px; selection-background-color:#28657e; selection-color:#ffffff;}
QComboBox QAbstractItemView {background:%(card)s; color:%(fg)s; selection-background-color:#28657e; selection-color:#ffffff;}
QComboBox::drop-down {border:0; width:22px;}
QComboBox::down-arrow {image:url("%(arrow)s"); width:14px; height:10px;}
QGroupBox {border:1px solid %(edge)s; border-radius:9px; margin-top:18px; padding:15px; font-weight:600;}
QGroupBox::title {subcontrol-origin:margin; left:14px; padding:0 5px;}
QProgressBar {border:0; background:%(tab)s; border-radius:4px; height:8px;}
QProgressBar::chunk {background:#18a2a0; border-radius:4px;}
QSplitter::handle {background:%(edge)s; width:5px;}
QToolTip {background:%(card)s; color:%(fg)s; border:1px solid %(edge)s; padding:5px;}
''' % colors
