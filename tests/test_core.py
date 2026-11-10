import json
from pathlib import Path
import pytest
from docx import Document
from scholarstyle.documents import chunks, diff_html, extract, export_word
from scholarstyle.storage import Library, load_profile, retrieve
from scholarstyle.revision import checks, revise
from scholarstyle.llm import Ollama
from scholarstyle.discovery import OpenAlex, pdf_url

TEXT = ('We investigated neuronal activity in cultured networks. '
        'These findings suggest that coordinated activity may support network maturation. ' * 40)

@pytest.fixture
def corpus(tmp_path):
    path = tmp_path / 'paper.docx'
    doc = Document(); doc.add_paragraph(TEXT); doc.save(path)
    library = Library(tmp_path / 'data')
    assert library.import_file(path)
    return library, path


def test_import_dedup_and_tables(corpus):
    library, path = corpus
    assert not library.import_file(path)
    assert len(library.papers()) == 1
    doc = Document(); doc.add_paragraph(TEXT)
    doc.add_table(rows=1, cols=1).cell(0,0).text = 'Table retained'
    doc.add_paragraph('After table'); doc.save(path)
    value = extract(path)
    assert value.index('Table retained') < value.index('After table')


def test_lossless_chunks():
    for value in [TEXT, 'x'*14000, '你好。'*2000, TEXT+'\n\n']:
        parts = list(chunks(value, 300))
        assert ''.join(parts) == value
        assert max(map(len,parts)) <= 300


def test_snapshot_update_cancel_and_frozen(corpus):
    library, path = corpus
    ids = [x['id'] for x in library.papers()]
    p = library.train(ids,'Supervisor',None,lambda s: None,lambda: False)
    snapshot = library.root / 'frozen_style.sqlite'
    previous = snapshot.read_bytes()
    assert p['version'] == 1
    assert retrieve(snapshot, 'neuronal network maturation')
    with pytest.raises(InterruptedError):
        library.train(ids,'Changed',None,lambda s: None,lambda: True)
    assert previous == snapshot.read_bytes()
    p = library.train(ids,'Supervisor',None,lambda s: None,lambda: False)
    assert p['version'] == 2
    assert (library.root / 'frozen_style.previous.sqlite').read_bytes() == previous
    library.remove(ids)
    assert retrieve(snapshot, 'neuronal')


class FakeModel:
    model = 'fake-test-model'
    def chat(self, system, payload):
        return {'revised': payload['draft'].replace('investigated', 'examined'),
                'explanation': '词语修改', 'warnings': []}


def test_revision_checkpoint_and_exports(corpus, tmp_path):
    library, _ = corpus
    library.train([x['id'] for x in library.papers()],'Team',None,lambda s: None,lambda: False)
    recovery = tmp_path/'revision.json'
    records = []
    session = revise(TEXT,library.root/'frozen_style.sqlite',FakeModel(),'',lambda s: None,lambda: False, records.append,recovery)
    assert session['complete']
    assert ''.join(r['original'] for r in records) == TEXT
    assert ''.join(r['revised'] for r in records) == TEXT.replace('investigated','examined')
    assert json.loads(recovery.read_text(encoding='utf-8'))['complete']
    for marked in [True,False]:
        path = tmp_path / f'{marked}.docx'; export_word(path,records,marked)
        doc = Document(path)
        assert 'examined' in '\n'.join(p.text for p in doc.paragraphs)
        if marked:
            assert any(run.font.strike for p in doc.paragraphs for run in p.runs)


def test_guardrails_and_html():
    assert len(checks('We found no effect (Smith, 2021), n=12.', 'We found an effect (Smith, 2022), n=13.')) == 3
    rendered = diff_html('<script>bad</script>', 'good')
    assert '<script>' not in rendered and '&lt;script&gt;' in rendered
    for endpoint in ['https://example.org', 'http://localhost.evil.test', 'http://user:pass@localhost', 'http://127.0.0.1/api/chat']:
        with pytest.raises(ValueError): Ollama(endpoint=endpoint)
    with pytest.raises(ValueError): Ollama(model='qwen-cloud')


def test_cancel_revision_incomplete(corpus, tmp_path):
    library, _ = corpus
    library.train([x['id'] for x in library.papers()],'Team',None,lambda s: None,lambda: False)
    recovery = tmp_path/'revision.json'
    with pytest.raises(InterruptedError):
        revise(TEXT,library.root/'frozen_style.sqlite',FakeModel(),'',lambda s: None,lambda: True,lambda r: None,recovery)
    assert not json.loads(recovery.read_text(encoding='utf-8'))['complete']


def test_metadata_only_is_not_downloadable():
    assert pdf_url({'best_oa_location': {'is_oa': True, 'landing_page_url':'https://example.org'}}) is None
    assert pdf_url({'locations':[{'is_oa':True,'pdf_url':'https://example.org/test.pdf'}]})


def test_pagination():
    client = OpenAlex()
    calls = []
    def get(entity, params):
        calls.append(params)
        return {'results':list(range(params['per_page'])), 'meta': {'next_cursor': 'next'}}
    client.get = get
    assert len(client.works('https://openalex.org/A123',150,lambda s:None,lambda:False)) == 150
    assert [c['per_page'] for c in calls] == [100,50]


def test_pdf_scan_message(tmp_path):
    from pypdf import PdfWriter
    path = tmp_path/'scan.pdf'
    writer = PdfWriter(); writer.add_blank_page(width=612,height=792)
    with path.open('wb') as stream: writer.write(stream)
    with pytest.raises(ValueError, match='OCR'): extract(path)


def test_failed_training_preserves_model(corpus):
    library, _ = corpus
    ids = [p['id'] for p in library.papers()]
    library.train(ids,'Team',None,lambda s:None,lambda:False)
    path = library.root/'frozen_style.sqlite'; before = path.read_bytes()
    class Broken:
        def chat(self, *args): return {'rules': 'wrong type'}
    with pytest.raises(ValueError): library.train(ids,'Team',Broken(),lambda s:None,lambda:False)
    assert path.read_bytes() == before
    assert not list(library.root.glob('training-*'))


def test_block_private_download_addresses(monkeypatch):
    from scholarstyle.discovery import public_url
    import socket
    monkeypatch.setattr(socket,'getaddrinfo',lambda *args:[(2,1,6,'',('127.0.0.1',80))])
    with pytest.raises(ValueError, match='非公网'): public_url('https://example.org/paper.pdf')
    with pytest.raises(ValueError): public_url('file:///tmp/paper.pdf')


def test_incomplete_llm_response_rejected():
    client = Ollama()
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'done':True,'done_reason':'length','message':{'content':'{"revised":"truncated"}'}}
    client.session.post = lambda *a,**k: Response()
    with pytest.raises(ValueError, match='截断'): client.chat('system',{})


def test_streamed_pdf_download_and_size_limit(tmp_path, monkeypatch):
    import scholarstyle.discovery as discovery
    class Response:
        is_redirect = False
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def iter_content(self, size): yield b'%PDF-1.7\n'; yield b'synthetic payload'
    class Session:
        def get(self, *args, **kwargs):
            assert kwargs['stream'] and not kwargs['allow_redirects']
            return Response()
        def close(self): pass
    monkeypatch.setattr(discovery,'public_url',lambda url:None)
    monkeypatch.setattr(discovery.requests,'Session',Session)
    path = tmp_path/'download.pdf'
    discovery.download_pdf('https://example.org/paper',path,lambda s:None,lambda:False)
    assert path.read_bytes().startswith(b'%PDF-')
    monkeypatch.setattr(discovery,'MAX_BYTES',8)
    with pytest.raises(ValueError, match='512 MB'):
        discovery.download_pdf('https://example.org/paper',path,lambda s:None,lambda:False)


def test_non_pdf_download_is_rejected(tmp_path, monkeypatch):
    import scholarstyle.discovery as discovery
    class Response:
        is_redirect=False
        headers={}
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def raise_for_status(self): pass
        def iter_content(self,size): yield b'<html>Sign in</html>'
    class Session:
        def get(self,*args,**kwargs): return Response()
        def close(self): pass
    monkeypatch.setattr(discovery,'public_url',lambda url:None)
    monkeypatch.setattr(discovery.requests,'Session',Session)
    with pytest.raises(ValueError, match='网页'):
        discovery.download_pdf('https://example.org/paper',tmp_path/'paper.pdf',lambda s:None,lambda:False)


def test_reference_copy_warning():
    from scholarstyle.revision import reference_overlap
    copied = 'These findings should be interpreted cautiously given the limited sample size.'
    evidence = [{'text': copied}]
    assert reference_overlap('We examined 12 cultures.', copied, evidence)
    assert not reference_overlap(copied, copied, evidence)
