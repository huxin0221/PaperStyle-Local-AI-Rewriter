import requests
import pytest
from scholarstyle import discovery


def paper():
    return {'id': 'W1', 'locations': [
        {'is_oa': True, 'pdf_url': 'https://example.org/one'},
        {'is_oa': True, 'pdf_url': 'https://example.org/two'}]}


def test_import_tries_alternative_copy(monkeypatch):
    calls = []
    def download(url, *args):
        calls.append(url)
        if len(calls) == 1:
            raise requests.HTTPError('blocked')
    monkeypatch.setattr(discovery, 'download_pdf', download)
    class Library:
        def import_file(self, *args): return 1
    result = discovery.import_works([paper()], Library(), lambda x: None, lambda: False)
    assert len(calls) == 2
    assert result == {'imported': 1, 'skipped': []}


def test_failure_status_without_credentials():
    response = requests.Response()
    response.status_code = 403
    error = requests.HTTPError('https://example.org/?token=secret', response=response)
    message = discovery.download_failure(error)
    assert '403' in message and 'secret' not in message


def test_cancellation_does_not_try_other_sources(monkeypatch):
    def download(*args): raise InterruptedError()
    monkeypatch.setattr(discovery, 'download_pdf', download)
    with pytest.raises(InterruptedError):
        discovery.import_works([paper()], None, lambda x: None, lambda: False)
