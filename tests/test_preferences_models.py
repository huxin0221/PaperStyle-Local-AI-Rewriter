import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PyQt5 import QtWidgets as W
from scholarstyle import gui, runtime
from scholarstyle.i18n import translate
from scholarstyle.llm import Ollama


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setattr(gui, 'system_is_dark', lambda: False)
    app = W.QApplication.instance() or W.QApplication([])
    app.setStyle('Fusion')
    w = gui.Window(tmp_path)
    yield w
    w.close()
    app.processEvents()


def test_language_switch_preserves_content(window):
    draft = 'Our manuscript remains in English. n = 12.'
    window.draft.setPlainText(draft)
    window.instruction.setText('Keep names unchanged')
    window.api_key.setText('secret-not-saved')
    for language, tab in [('de', '② Entwurfsstudio'), ('en', '② Draft studio'), ('zh', '② 草稿工作室')]:
        window.language_box.setCurrentIndex(window.language_box.findData(language))
        assert window.tabs.tabText(1) == tab
        assert window.draft.toPlainText() == draft
        assert window.instruction.text() == 'Keep names unchanged'
        assert window.api_key.text() == 'secret-not-saved'
    settings = json.loads(window.preferences_path.read_text())
    assert 'secret-not-saved' not in json.dumps(settings)


def test_all_chrome_has_three_languages(window):
    import re
    for language in ('en', 'de'):
        for _, source in window._bindings:
            if re.search('[\u4e00-\u9fff]', source):
                assert not re.search('[\u4e00-\u9fff]', translate(source, language)), source


def test_model_selection_sync_refresh_and_persistence(window):
    window.draft_model.setCurrentText('qwen2.5:14b')
    assert window.model.currentText() == 'qwen2.5:14b'
    assert window.client().model == 'qwen2.5:14b'
    window.models_ready(['qwen2.5:7b', 'my-custom-local:latest'])
    assert window.model.currentText() == 'qwen2.5:14b'
    assert window.model.findText('my-custom-local:latest') >= 0
    window.model.setCurrentText('my-custom-local:latest')
    assert window.draft_model.currentText() == 'my-custom-local:latest'
    assert 'my-custom-local:latest' in window.active_workflow.text()
    assert 'my-custom-local:latest' == json.loads(window.preferences_path.read_text())['model']


def test_dark_light_system_and_restore(window, monkeypatch):
    window.language_box.setCurrentIndex(window.language_box.findData('de'))
    window.theme_box.setCurrentIndex(window.theme_box.findData('dark'))
    window.show(); W.QApplication.processEvents()
    assert window._dark
    assert window.model.palette().base().color().lightness() < 100
    window.theme_box.setCurrentIndex(window.theme_box.findData('light'))
    assert not window._dark
    assert window.model.palette().base().color().lightness() > 200
    window.theme_box.setCurrentIndex(window.theme_box.findData('system'))
    monkeypatch.setattr(gui, 'system_is_dark', lambda: True)
    window.follow_system_theme()
    assert window._dark
    other = gui.Window(window.root)
    assert other.language == 'de'
    assert other.theme_mode == 'system' and other._dark
    other.close()


def test_local_model_and_language_reach_draft_pipeline(window, monkeypatch):
    # Keep the test deterministic: no download, server or model invocation.
    window.snapshot.touch()
    window.draft.setPlainText('We studied neuronal activity in 12 cultures for seven days. This is our draft.')
    window.model.setCurrentText('qwen2.5:14b')
    window.language_box.setCurrentIndex(window.language_box.findData('de'))
    calls = []
    monkeypatch.setattr(gui, 'prepare', lambda client,p,c: calls.append(('prepare',client.model)))
    def revise(text,snapshot,client,instruction,p,c,r,recovery,language):
        calls.append(('revise',client.model,language,text,snapshot))
        return {'records': [], 'complete': True}
    monkeypatch.setattr(gui, 'revise', revise)
    monkeypatch.setattr(window,'run',lambda task,callback: callback(task(lambda s:None,lambda:False,lambda r:None)))
    window.start_revision()
    assert calls[0] == ('prepare', 'qwen2.5:14b')
    assert calls[1][0:3] == ('revise', 'qwen2.5:14b', 'de')
    assert calls[1][3] == window.draft.toPlainText()
    assert calls[1][4] == window.snapshot


def test_translations_preserve_user_values():
    assert translate('本地修改 · 2/8 段块','de') == 'Lokale Überarbeitung · Abschnitt 2/8'
    assert translate('模型状态：已安装','en') == 'Model status: 已安装'  # placeholders are data, not recursively translated
    assert translate('数据目录：/tmp/{my folder}','en') == 'Data directory: /tmp/{my folder}'
    assert translate('Downloading the official Ollama installer…','zh') == '正在下载官方 Ollama 安装程序…'


class FakeClient:
    model = 'qwen2.5:7b'
    endpoint = 'http://127.0.0.1:11434'
    def __init__(self): self.names = []; self.pulls = 0
    def models(self): return self.names
    def pull(self,p,c): self.pulls += 1; self.names = [self.model]


def test_prepare_downloads_only_missing_model():
    client = FakeClient()
    assert runtime.prepare(client,lambda s:None,lambda:False) == [client.model]
    assert client.pulls == 1
    runtime.prepare(client,lambda s:None,lambda:False)
    assert client.pulls == 1


def test_missing_runtime_installs_then_starts(monkeypatch):
    import requests
    client = FakeClient()
    client.models = lambda: (_ for _ in ()).throw(requests.ConnectionError())
    calls = []
    monkeypatch.setattr(runtime,'executable',lambda:None)
    monkeypatch.setattr(runtime,'install_runtime',lambda p,c: calls.append('install') or '/test/ollama')
    monkeypatch.setattr(runtime,'start_server',lambda *args: calls.append('start') or [client.model])
    assert runtime.prepare(client,lambda s:None,lambda:False) == [client.model]
    assert calls == ['install','start']


def test_prepare_cancel_and_custom_endpoint(monkeypatch):
    import requests
    client = FakeClient()
    with pytest.raises(InterruptedError): runtime.prepare(client,lambda s:None,lambda:True)
    client.endpoint = 'http://127.0.0.1:9999'
    client.models = lambda: (_ for _ in ()).throw(requests.ConnectionError())
    with pytest.raises(ValueError,match='自定义'): runtime.prepare(client,lambda s:None,lambda:False)


def test_incomplete_download_is_not_success():
    client = Ollama()
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def raise_for_status(self): pass
        def iter_lines(self): yield b'{"status":"pulling manifest"}'
    client.session.post = lambda *a,**kw: Response()
    with pytest.raises(ValueError,match='未完成'): client.pull(lambda s:None,lambda:False)


def test_runtime_update_verifies_running_version(monkeypatch):
    from types import SimpleNamespace
    client = FakeClient(); client.names = [client.model]
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'version':'1.2.3'}
    client.session = SimpleNamespace(get=lambda *a,**kw:Response())
    monkeypatch.setattr(runtime,'install_runtime',lambda *a,**kw:'/test/ollama')
    monkeypatch.setattr(runtime,'executable',lambda:'/test/ollama')
    monkeypatch.setattr(runtime.subprocess,'run',lambda *a,**kw:SimpleNamespace(stdout='ollama version is 1.2.3',stderr=''))
    monkeypatch.setattr(runtime,'start_server',lambda *a:pytest.fail('Updated server already running'))
    assert runtime.prepare(client,lambda s:None,lambda:False,update=True) == [client.model]


def test_explanation_language_does_not_translate_manuscript(tmp_path, monkeypatch):
    from scholarstyle import revision
    monkeypatch.setattr(revision,'load_profile',lambda path:{'rules':[],'mean_sentence_words':12,'top_terms':[]})
    monkeypatch.setattr(revision,'retrieve',lambda *a:[])
    draft = 'We examined neuronal activity in 12 cultures.'
    class Model:
        model = 'selected-local-model'
        def chat(self, system, payload):
            assert 'warnings in German' in system
            assert 'Preserve the original manuscript language' in system
            assert payload['draft'] == draft
            return {'revised':draft,'explanation':'Keine Änderung erforderlich.','warnings':[]}
    session = revision.revise(draft,tmp_path/'snapshot',Model(),'',lambda s:None,lambda:False,
                              lambda r:None,tmp_path/'result.json',language='de')
    assert session['model'] == 'selected-local-model'
    assert session['interface_language'] == 'de'
    assert session['records'][0]['revised'] == draft


def test_installer_rejects_unsupported_macos_before_download(monkeypatch):
    from scholarstyle import ollama_install
    monkeypatch.setattr(ollama_install.platform,'system',lambda:'Darwin')
    monkeypatch.setattr(ollama_install.platform,'mac_ver',lambda:('13.7',(),''))
    monkeypatch.setattr(ollama_install.urllib.request,'urlopen',lambda *a,**kw:pytest.fail('Must not download on unsupported OS'))
    with pytest.raises(RuntimeError,match='macOS 14'):
        ollama_install.install_runtime(lambda s:None,lambda:False)
