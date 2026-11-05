from pathlib import Path
import os
import sys
import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@pytest.fixture(scope='session', autouse=True)
def qapp():
    from software.qt_bootstrap import configure_qt_plugins
    configure_qt_plugins()
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


@pytest.fixture
def window(qapp, monkeypatch):
    from PyQt5 import QtWidgets
    from software.gui.main_window import MainWindow
    messages = []
    for kind in ('warning', 'critical', 'information'):
        monkeypatch.setattr(QtWidgets.QMessageBox, kind, lambda *a: messages.append(a[2]))
    win = MainWindow()
    win._test_messages = messages
    yield win
    if win.worker:
        win.client.request_abort()
        win.worker.wait(10000)
        qapp.processEvents()
    win.close()
    qapp.processEvents()
