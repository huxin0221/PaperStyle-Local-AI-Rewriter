"""Keep one QApplication alive throughout the suite, as required by Qt."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PyQt5 import QtWidgets as W


@pytest.fixture(scope='session', autouse=True)
def qt_application():
    app = W.QApplication.instance() or W.QApplication([])
    yield app
