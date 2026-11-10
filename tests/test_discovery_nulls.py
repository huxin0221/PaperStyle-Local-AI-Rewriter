from scholarstyle.discovery import OpenAlex, pdf_url


def test_null_author_results(monkeypatch):
    client = OpenAlex()
    monkeypatch.setattr(client, 'get', lambda *args: {'results': None})
    assert client.authors('Hayder Amin') == []


def test_null_work_results(monkeypatch):
    client = OpenAlex()
    monkeypatch.setattr(client, 'get', lambda *args: {'results': None, 'meta': None})
    assert client.works('A123', 100, lambda message: None, lambda: False) == []


def test_null_pagination_metadata(monkeypatch):
    client = OpenAlex()
    paper = {'id': 'W123', 'locations': None, 'best_oa_location': None}
    monkeypatch.setattr(client, 'get', lambda *args: {'results': [paper], 'meta': None})
    assert client.works('A123', 100, lambda message: None, lambda: False) == [paper]
    assert pdf_url(paper) is None


def test_null_locations_preserves_best_pdf():
    assert pdf_url({'locations': None, 'best_oa_location': {
        'is_oa': True, 'pdf_url': 'https://example.org/paper.pdf'
    }}) == 'https://example.org/paper.pdf'
