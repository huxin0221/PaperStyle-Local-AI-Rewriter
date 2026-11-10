"""Ollama client restricted to this computer; no remote manuscript inference."""
import json
import requests
import time
from urllib.parse import urlparse
from .training import STYLE_OPTIONS


class Ollama:
    def __init__(self, model='qwen2.5:7b', endpoint='http://127.0.0.1:11434'):
        parsed = urlparse(endpoint)
        if parsed.scheme not in ('http', 'https') or parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('仅允许本机 Ollama 地址。')
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
            raise ValueError('请输入本机 Ollama 根地址，例如 http://127.0.0.1:11434')
        if not model.strip() or 'cloud' in model.lower() or '/' in model:
            raise ValueError('请输入本地模型名称；不支持云端模型或远程模型路径。')
        self.model, self.endpoint = model.strip(), endpoint.rstrip('/')
        self.session = requests.Session()
        self.session.trust_env = False

    def models(self):
        response = self.session.get(self.endpoint + '/api/tags', timeout=(5, 15), allow_redirects=False)
        response.raise_for_status()
        return [x['name'] for x in response.json().get('models', [])]

    def pull(self, progress, cancelled):
        success = False
        with self.session.post(self.endpoint + '/api/pull', json={'model': self.model, 'stream': True},
                               timeout=(5, 60), stream=True, allow_redirects=False) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if cancelled():
                    raise InterruptedError('下载已取消')
                if line:
                    item = json.loads(line)
                    if item.get('error'):
                        raise ValueError(item['error'])
                    success = success or item.get('status') == 'success'
                    progress(item.get('status', '') + (f" · {item.get('completed', 0) / item['total']:.0%}" if item.get('total') else ''))
        if cancelled():
            raise InterruptedError('下载已取消')
        if not success:
            raise ValueError('模型下载未完成，请重试以继续下载。')
        return '模型已下载：' + self.model

    def chat(self, system, payload):
        # A concrete schema is more reliable than JSON mode alone on small local models.
        if 'draft' in payload:
            schema = {'type': 'object', 'properties': {
                'revised': {'type': 'string'}, 'explanation': {'type': 'string'},
                'warnings': {'type': 'array', 'items': {'type': 'string'}}},
                'required': ['revised', 'explanation', 'warnings'], 'additionalProperties': False}
        else:
            schema = {'type': 'object', 'properties': {
                'rules': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 16}},
                'required': ['rules'], 'additionalProperties': False}
        response = self.session.post(self.endpoint + '/api/chat', json={
            'model': self.model, 'stream': False, 'think': False, 'format': schema,
            'messages': [{'role': 'system', 'content': system},
                         {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}],
            'options': {'temperature': 0.15, 'num_ctx': 8192, 'num_predict': 3072},
            'keep_alive': '5m'}, timeout=(5, 600), allow_redirects=False)
        response.raise_for_status()
        data = response.json()
        if data.get('error') or not data.get('done') or data.get('done_reason') == 'length':
            raise ValueError('模型输出失败或被截断：' + str(data.get('error', data.get('done_reason'))))
        result = json.loads(data['message']['content'])
        if not isinstance(result, dict):
            raise ValueError('模型未返回 JSON 对象，请重试。')
        return result

    def style_identity(self):
        """Include the weights digest so replacing a tag invalidates style caches."""
        response = self.session.get(self.endpoint + '/api/tags', timeout=(5, 15), allow_redirects=False)
        response.raise_for_status()
        for item in response.json().get('models', []):
            if item.get('name') in (self.model, self.model + ':latest') and item.get('digest'):
                return self.model + '@' + item['digest']
        raise ValueError('选中模型尚未安装。请先下载模型。')

    def style_chat(self, system, payload, cancelled, tick):
        """Small, streamed training requests; manuscript revision keeps its own budget."""
        if cancelled():
            raise InterruptedError('训练已取消，原冻结模型保留。')
        schema = {'type': 'object', 'properties': {'rules': {
            'type': 'array', 'minItems': 1, 'maxItems': 6,
            'items': {'type': 'string', 'minLength': 1, 'maxLength': 180}}},
            'required': ['rules'], 'additionalProperties': False}
        started = last_update = time.monotonic()
        pieces, size, done = [], 0, False
        with self.session.post(self.endpoint + '/api/chat', json={
            'model': self.model, 'stream': True, 'think': False, 'format': schema,
            'messages': [{'role': 'system', 'content': system},
                         {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}],
            'options': dict(STYLE_OPTIONS), 'keep_alive': '10m'},
            timeout=(5, 120), stream=True, allow_redirects=False) as response:
            response.raise_for_status()
            for line in response.iter_lines(chunk_size=1):
                if cancelled():
                    raise InterruptedError('训练已取消，原冻结模型保留。')
                current = time.monotonic()
                if current-started > 420:
                    raise TimeoutError('风格学习请求超时，请使用更小的本地模型后重试。')
                if not line:
                    continue
                item = json.loads(line)
                if item.get('error') or item.get('done_reason') == 'length':
                    raise ValueError('模型输出失败或被截断：' + str(item.get('error', item.get('done_reason'))))
                fragment = item.get('message', {}).get('content', '')
                pieces.append(fragment); size += len(fragment)
                if size > 20000:
                    raise ValueError('风格规则格式错误，原模型保留。')
                if current-last_update >= 1:
                    tick(int(current-started), size); last_update = current
                if item.get('done'):
                    done = True
                    break
        if cancelled():
            raise InterruptedError('训练已取消，原冻结模型保留。')
        if not done:
            raise ValueError('模型输出失败或被截断：incomplete stream')
        value = json.loads(''.join(pieces))
        if not isinstance(value, dict):
            raise ValueError('风格规则格式错误，原模型保留。')
        return value
