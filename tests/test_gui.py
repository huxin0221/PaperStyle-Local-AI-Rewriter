import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt5 import QtWidgets as W
from scholarstyle.gui import Window, THEME


def test_window(tmp_path):
    app = W.QApplication.instance() or W.QApplication([])
    app.setStyleSheet(THEME)
    window = Window(tmp_path)
    window.show(); app.processEvents()
    assert window.tabs.count() == 2
    assert window.paper_sources.count() == 2
    assert window.paper_sources.isVisible()
    assert window.library_scroll.isVisible()
    window.paper_sources.setCurrentIndex(1)
    app.processEvents()
    assert window.author_name.isVisible()
    window.paper_sources.setCurrentIndex(0)
    assert window.papers.isVisible()
    assert window.paper_sources.isAncestorOf(window.author_name)
    assert window.paper_sources.isAncestorOf(window.papers)
    window.settings_dialog.show(); app.processEvents()
    assert window.settings_dialog.isVisible()
    assert not window.use_llm.isChecked()
    assert window.papers.count() == 0
    assert not window.cancel.isEnabled()
    window.close()


def test_manual_edits_invalidate_approval_and_persist(tmp_path):
    import json
    app = W.QApplication.instance() or W.QApplication([])
    window = Window(tmp_path)
    record = {'index':0,'original':'We examined 12 cultures.','revised':'We examined 12 cultures.',
              'explanation':'','warnings':[],'references':[],'accepted':True}
    window.session = {'complete':True,'records':[record]}
    window.add_record(record)
    assert window.records[0]['accepted']
    window.editor.setPlainText('We examined 13 cultures.')
    assert not window.records[0]['accepted']
    assert window.records[0]['warnings']
    saved = json.loads(window.recovery.read_text(encoding='utf-8'))
    assert saved['records'][0]['revised'] == 'We examined 13 cultures.'
    window.revert()
    assert window.records[0]['revised'] == 'We examined 12 cultures.'
    assert window.records[0]['accepted']
    window.close()

def test_online_train_imports_selected_papers(tmp_path, monkeypatch):
    from scholarstyle import gui
    app = W.QApplication.instance() or W.QApplication([])
    window = Window(tmp_path)
    window.works = [{'id': 'W1', 'display_name': 'Selected paper'}]
    item = W.QListWidgetItem('Selected paper')
    item.setData(gui.C.Qt.UserRole, 0)
    item.setCheckState(gui.C.Qt.Checked)
    window.work_list.addItem(item)
    window.paper_sources.setCurrentIndex(1)
    calls = []
    def imported(works, library, progress, cancelled):
        calls.append(works)
        from scholarstyle.storage import connect
        with connect(library.path) as db:
            db.execute('INSERT INTO papers VALUES (?,?,?,?,?)',
                       ('p1', 'Selected paper', 'W1', 'Scientific prose about careful experiments. ' * 20, 'now'))
        return {'imported': 1, 'skipped': []}
    monkeypatch.setattr(gui, 'import_works', imported)
    monkeypatch.setattr(window, 'run', lambda task, callback: callback(task(lambda x: None, lambda: False, lambda x: None)))
    window.train()
    assert calls == [window.works]
    from scholarstyle.storage import load_profile
    assert load_profile(window.snapshot)['papers'][0]['id'] == 'p1'
    assert window.paper_sources.currentIndex() == 0
    window.close()

def test_compact_window_keeps_search_controls_readable(tmp_path):
    app = W.QApplication.instance() or W.QApplication([])
    window = Window(tmp_path)
    window.resize(1100, 720)
    window.paper_sources.setCurrentIndex(1)
    window.show()
    app.processEvents()
    assert window.profile_name.text() == 'Frozen Style'
    assert window.profile_name.isHidden()
    assert window.author_name.height() >= window.author_name.minimumSizeHint().height()
    assert window.work_list.height() >= 140
    assert window.library_scroll.verticalScrollBar().maximum() > 0
    window.close()
