"""Prepare the same selected local model for both style learning and editing."""
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse
import requests
from .ollama_install import install_runtime, InstallCancelled

# Stable text-capable options; editable selectors also accept installed/custom tags.
PRESETS = ('qwen2.5:3b', 'qwen2.5:7b', 'qwen2.5:14b', 'qwen2.5:32b',
           'gemma3:4b', 'gemma3:12b', 'gemma3:27b')


def executable():
    for candidate in (Path.home()/'Applications/Ollama.app/Contents/Resources/ollama',
                      Path('/Applications/Ollama.app/Contents/Resources/ollama'),
                      Path(os.environ.get('LOCALAPPDATA', ''))/'Programs/Ollama/ollama.exe'):
        if candidate.is_file():
            return str(candidate)
    return shutil.which('ollama')


def check_cancel(cancelled):
    if cancelled():
        raise InterruptedError('任务已取消')


def default_server(client):
    url = urlparse(client.endpoint)
    return url.scheme == 'http' and (url.port or 80) == 11434


def start_server(client, binary, progress, cancelled):
    check_cancel(cancelled)
    progress('正在启动本机 Ollama…')
    folder = Path.home()/'.ollama/logs'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder/'scholarstyle-startup.log').open('ab') as log:
        subprocess.Popen([binary, 'serve'], stdout=log, stderr=log,
            start_new_session=os.name != 'nt', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    for _ in range(45):
        check_cancel(cancelled)
        try:
            return client.models()
        except requests.ConnectionError:
            time.sleep(1)
    raise RuntimeError('Ollama 启动失败。请查看 ~/.ollama/logs/scholarstyle-startup.log。')


def prepare(client, progress, cancelled, download=True, update=False):
    check_cancel(cancelled)
    progress('正在检查本机 Ollama 和选中模型…')
    if update:
        if not default_server(client):
            raise ValueError('自动安装 / 更新仅支持默认本机端口 11434。')
        binary = install_runtime(progress, cancelled, upgrade=bool(executable()))
        version = subprocess.run([binary, '--version'], capture_output=True, text=True, timeout=15,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        versions = re.findall(r'\b\d+\.\d+\.\d+\b', version.stdout + ' ' + version.stderr)
        if not versions:
            raise RuntimeError('无法验证新安装的 Ollama 版本，请手动检查安装。')
        installed_version = versions[-1]
        server_ready = False
        # Installer shuts down the previous runtime. Wait for the port to release.
        for _ in range(20):
            check_cancel(cancelled)
            try:
                response = client.session.get(client.endpoint + '/api/version', timeout=(2, 3), allow_redirects=False)
                response.raise_for_status()
                if response.json().get('version') == installed_version:
                    server_ready = True
                    break
            except requests.ConnectionError:
                break
            time.sleep(.25)
        else:
            raise RuntimeError('旧版 Ollama 仍在运行。请退出 Ollama 后重试。')
        names = client.models() if server_ready else start_server(client, binary, progress, cancelled)
    else:
        try:
            names = client.models()
        except requests.ConnectionError:
            if not default_server(client):
                raise ValueError('无法连接自定义本机服务。请手动启动该地址的 Ollama。')
            binary = executable()
            if not binary:
                if not download:
                    raise ValueError('未安装 Ollama。请点击「下载 / 准备选中模型」。')
                binary = install_runtime(progress, cancelled)
            names = start_server(client, binary, progress, cancelled)
    check_cancel(cancelled)
    if client.model not in names and client.model + ':latest' not in names:
        if not download:
            raise ValueError('选中模型尚未安装。请先下载模型。')
        progress('正在下载模型：' + client.model)
        client.pull(progress, cancelled)
        names = client.models()
        if client.model not in names and client.model + ':latest' not in names:
            raise ValueError('下载结束后未找到选中模型，请重试。')
    check_cancel(cancelled)
    return names


def probe(client, progress, cancelled):
    names = prepare(client, progress, cancelled, download=False)
    progress('正在测试选中模型的短文本响应…')
    check_cancel(cancelled)
    result = client.session.post(client.endpoint + '/api/chat', json={
        'model': client.model, 'stream': False,
        'messages': [{'role': 'user', 'content': 'Reply only with OK.'}],
        'options': {'num_ctx': 2048, 'num_predict': 24}},
        timeout=(5, 180), allow_redirects=False)
    result.raise_for_status()
    data = result.json()
    check_cancel(cancelled)
    text = data.get('message', {}).get('content', '').strip()
    if not data.get('done') or not text or data.get('error'):
        raise ValueError('选中模型未返回完整响应，请检查内存和模型兼容性。')
    return names, text[:120]
