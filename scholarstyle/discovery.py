"""Author disambiguation and streamed open-access full-text imports."""
import ipaddress
import socket
import tempfile
from pathlib import Path
from urllib.parse import urlparse, urljoin
import requests
from .documents import MAX_BYTES


class OpenAlex:
    def __init__(self, api_key=''):
        self.key = api_key.strip()

    def get(self, entity, params):
        if self.key:
            params = dict(params, api_key=self.key)
        response = requests.get('https://api.openalex.org/' + entity, params=params, timeout=(10, 45))
        if response.status_code != 200:
            raise ValueError(f'OpenAlex 请求失败 ({response.status_code})。请检查网络、API key 或额度。')
        return response.json()

    def authors(self, name):
        if not name.strip():
            raise ValueError('请输入作者姓名。')
        return (self.get('authors', {'search': name.strip(), 'per_page': 20}).get('results') or [])

    def works(self, author_id, maximum, progress, cancelled):
        author_id = author_id.rsplit('/', 1)[-1]
        if not author_id.startswith('A') or not author_id[1:].isdigit():
            raise ValueError('无效 OpenAlex 作者 ID。')
        results, cursor = [], '*'
        while len(results) < maximum and cursor:
            if cancelled():
                raise InterruptedError('检索已取消')
            data = self.get('works', {'filter': f'authorships.author.id:{author_id},is_retracted:false',
                                      'sort': 'publication_date:desc', 'per_page': min(100, maximum-len(results)), 'cursor': cursor})
            batch = data.get('results') or []
            results.extend(batch)
            progress(f'已检索 {len(results)} 篇论文')
            cursor = (data.get('meta') or {}).get('next_cursor') if batch else None
        return results


def public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('论文下载地址无效。')
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80))
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('拒绝下载非公网地址。')


def download_pdf(url, path, progress, cancelled):
    session = requests.Session()
    try:
        for _ in range(6):
            public_url(url)
            with session.get(url, timeout=(10, 45), stream=True, allow_redirects=False,
                             headers={'User-Agent': 'ScholarStyleStudio/0.1 (academic writing assistant)'}) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers['Location'])
                    continue
                response.raise_for_status()
                if int(response.headers.get('Content-Length', 0)) > MAX_BYTES:
                    raise ValueError('论文 PDF 超过 512 MB。')
                size = 0
                with open(path, 'wb') as target:
                    for block in response.iter_content(1024 * 256):
                        if cancelled():
                            raise InterruptedError('下载已取消')
                        size += len(block)
                        if size > MAX_BYTES:
                            raise ValueError('论文 PDF 超过 512 MB。')
                        target.write(block)
                        progress(f'下载论文 · {size / 1024 / 1024:.1f} MB')
                with open(path, 'rb') as downloaded:
                    if b'%PDF-' not in downloaded.read(1024):
                        raise ValueError('链接返回网页而非 PDF，请手动下载全文后导入。')
                return
        raise ValueError('下载重定向次数过多。')
    finally:
        session.close()


def pdf_urls(work):
    locations = [work.get('best_oa_location'), work.get('primary_location')] + (work.get('locations') or [])
    return list(dict.fromkeys(
        loc['pdf_url'] for loc in locations
        if isinstance(loc, dict) and loc.get('is_oa') and loc.get('pdf_url')
    ))


def pdf_url(work):
    return next(iter(pdf_urls(work)), None)


def download_failure(error):
    # Do not expose request URLs, which may contain credentials.
    if isinstance(error, requests.HTTPError):
        status = error.response.status_code if error.response is not None else 'unknown'
        return f'HTTP {status} (server refused or could not provide the PDF)'
    if isinstance(error, requests.Timeout):
        return 'Download timed out'
    if isinstance(error, requests.RequestException):
        return 'Network or TLS connection failed'
    if isinstance(error, ValueError):
        return str(error)
    return f'{type(error).__name__}: PDF could not be downloaded or parsed'


def import_works(works, library, progress, cancelled):
    imported, skipped = 0, []
    for work in works:
        if cancelled():
            raise InterruptedError('Import cancelled; imported papers are retained.')
        title = work.get('display_name') or work['id']
        urls = pdf_urls(work)
        if not urls:
            skipped.append(title + ': No public PDF link; download manually and import.')
            continue
        failures = []
        for index, url in enumerate(urls):
            if cancelled():
                raise InterruptedError('Import cancelled; imported papers are retained.')
            try:
                with tempfile.TemporaryDirectory(prefix='scholarstyle-') as folder:
                    path = Path(folder) / 'paper.pdf'
                    progress(f'Downloading {index + 1}/{len(urls)} sources: {title}')
                    download_pdf(url, path, progress, cancelled)
                    imported += library.import_file(path, progress, cancelled, title, work.get('doi') or work['id'])
                break
            except InterruptedError:
                raise
            except Exception as error:
                failures.append(download_failure(error))
        else:
            skipped.append(title + ': ' + '; '.join(dict.fromkeys(failures)) +
                           '. All listed public PDF sources failed; download in your browser and import the file.')
    return {'imported': imported, 'skipped': skipped}