"""SQLite corpus and atomically replaced, immutable-at-inference style snapshots."""
import collections
import hashlib
import json
import os
import re
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from .documents import chunks, extract
from .training import style_samples, cache_key, validate_rules, combine_rules, STYLE_SYSTEM, TRAINING_VERSION


def now():
    return datetime.now(timezone.utc).isoformat()


class ClosingConnection(sqlite3.Connection):
    """Finish the transaction and release file handles, including on Windows."""

    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def connect(path):
    db = sqlite3.connect(path, factory=ClosingConnection)
    db.row_factory = sqlite3.Row
    return db


class Library:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'library.sqlite'
        with connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS papers (id TEXT PRIMARY KEY, title TEXT, source TEXT, text TEXT, added TEXT)')

    def papers(self):
        with connect(self.path) as db:
            return [dict(r) for r in db.execute('SELECT id,title,source,length(text) AS characters,added FROM papers ORDER BY added')]

    def import_file(self, path, progress=lambda s: None, cancelled=lambda: False, title=None, source=None):
        text = extract(path, progress, cancelled)
        digest = hashlib.sha256(text.encode()).hexdigest()
        with connect(self.path) as db:
            cursor = db.execute('INSERT OR IGNORE INTO papers VALUES (?,?,?,?,?)',
                               (digest, title or Path(path).name, source or str(Path(path).resolve()), text, now()))
            return cursor.rowcount > 0

    def remove(self, ids):
        with connect(self.path) as db:
            db.executemany('DELETE FROM papers WHERE id=?', [(i,) for i in ids])

    def train(self, ids, name, llm, progress, cancelled, mode='fast'):
        if not ids:
            raise ValueError('请先勾选训练论文。')
        if mode not in ('fast', 'detailed'):
            raise ValueError('Unknown training mode: ' + mode)
        ids = list(dict.fromkeys(ids))
        started = time.monotonic()
        destination = self.root / 'frozen_style.sqlite'
        previous = load_profile(destination) if destination.exists() else None
        version = previous['version'] + 1 if previous else 1
        handle, temp_name = tempfile.mkstemp(prefix='training-', suffix='.sqlite', dir=self.root)
        os.close(handle)
        db = connect(temp_name)
        cache = connect(self.root / 'training_cache.sqlite')
        cache.execute('CREATE TABLE IF NOT EXISTS style_cache (key TEXT PRIMARY KEY, rules TEXT NOT NULL, created TEXT NOT NULL)')
        cache.commit()
        counts = collections.Counter()
        sentence_words = sentence_count = sample_count = total_characters = 0
        documents, plans, paper_rules = [], [], []
        calls = hits = analyzed_characters = 0

        def check_cancel():
            if cancelled():
                raise InterruptedError('训练已取消，原冻结模型保留。')

        try:
            check_cancel()
            db.execute('CREATE TABLE metadata (json TEXT NOT NULL)')
            db.execute('CREATE VIRTUAL TABLE samples USING fts5(text, title UNINDEXED, source UNINDEXED, paper_id UNINDEXED)')
            with connect(self.path) as corpus:
                for index, paper_id in enumerate(ids):
                    check_cancel()
                    row = corpus.execute('SELECT * FROM papers WHERE id=?', (paper_id,)).fetchone()
                    if row is None:
                        raise ValueError('训练论文已被移除，请刷新文献库。')
                    documents.append({k: row[k] for k in ('id', 'title', 'source')})
                    total_characters += len(row['text'])
                    # Full-corpus statistics and retrieval never depend on sampling.
                    for part in chunks(row['text']):
                        check_cancel()
                        words = re.findall(r"[A-Za-z][A-Za-z'-]+", part.lower())
                        counts.update(w for w in words if len(w) > 4)
                        for sentence in re.split(r'[.!?]+\s+', part):
                            if sentence.strip():
                                sentence_words += len(re.findall(r'\b\w+\b', sentence))
                                sentence_count += 1
                        db.execute('INSERT INTO samples VALUES (?,?,?,?)', (part, row['title'], row['source'], paper_id))
                        sample_count += 1
                    if llm:
                        plans.append((row['title'], style_samples(row['text'], mode)))
                    progress(f"全文索引 {index+1}/{len(ids)} · {row['title']}")
            # Fingerprint once per run; cached results are invalidated on model digest changes.
            check_cancel()
            identity = llm.style_identity() if llm and hasattr(llm, 'style_identity') else getattr(llm, 'model', type(llm).__name__)
            total = sum(len(samples) for _, samples in plans)
            completed = 0
            for title, samples in plans:
                rules_for_paper = []
                for sample in samples:
                    check_cancel()
                    key = cache_key(identity, sample)
                    cached = cache.execute('SELECT rules FROM style_cache WHERE key=?', (key,)).fetchone()
                    rules = None
                    if cached:
                        try:
                            rules = validate_rules({'rules': json.loads(cached['rules'])})
                        except (ValueError, TypeError):
                            pass
                    if rules is not None:
                        hits += 1
                        progress(f'缓存复用 {completed+1}/{total} · {title}')
                    else:
                        progress(f'风格学习 {completed}/{total} · {title}')
                        if hasattr(llm, 'style_chat'):
                            def tick(seconds, characters):
                                progress(f'风格学习 {completed}/{total} · {title} · {seconds}s / {characters} chars')
                            answer = llm.style_chat(STYLE_SYSTEM, {'paper_excerpts': sample}, cancelled, tick)
                        else:
                            answer = llm.chat(STYLE_SYSTEM, {'paper_excerpts': sample})
                        rules = validate_rules(answer)
                        # A completed response is recoverable even if the next sample is cancelled.
                        cache.execute('INSERT OR REPLACE INTO style_cache VALUES (?,?,?)',
                                      (key, json.dumps(rules, ensure_ascii=False), now()))
                        cache.commit()
                        calls += 1
                    analyzed_characters += len(sample)
                    rules_for_paper.extend(rules)
                    completed += 1
                    progress(f'风格学习 {completed}/{total} · {title}')
                paper_rules.append(list(dict.fromkeys(rules_for_paper)))
            check_cancel()
            rules = combine_rules(paper_rules)
            profile = {'schema': 1, 'version': version, 'name': name.strip() or 'Research Writing Style',
                       'created': now(), 'method': 'sampled-style-rules+full-corpus-fts' if llm else 'statistics+full-corpus-fts',
                       'llm': getattr(llm, 'model', None), 'papers': documents, 'chunks': sample_count,
                       'rules': rules, 'top_terms': counts.most_common(60),
                       'mean_sentence_words': round(sentence_words / max(sentence_count, 1), 1),
                       'training': {'version': TRAINING_VERSION, 'mode': mode if llm else 'statistics',
                                    'llm_calls': calls, 'cache_hits': hits, 'samples': completed,
                                    'sample_characters': analyzed_characters, 'corpus_characters': total_characters,
                                    'model_identity': identity if llm else None,
                                    'elapsed_seconds': round(time.monotonic()-started, 2)},
                       'paper_rules': [{'paper_id': doc['id'], 'rules': value}
                                       for doc, value in zip(documents, paper_rules)]}
            db.execute('INSERT INTO metadata VALUES (?)', (json.dumps(profile, ensure_ascii=False),))
            db.commit()
            db.close()
            check_cancel()
            if destination.exists():
                import shutil
                shutil.copy2(destination, self.root / 'frozen_style.previous.sqlite')
            os.replace(temp_name, destination)
            return profile
        finally:
            db.close()
            cache.close()
            Path(temp_name).unlink(missing_ok=True)


def load_profile(path):
    with connect(path) as db:
        value = json.loads(db.execute('SELECT json FROM metadata').fetchone()[0])
        if value.get('schema') != 1:
            raise ValueError('不支持此风格档案版本。')
        return value


def retrieve(path, text, limit=3):
    tokens = collections.Counter(re.findall(r'[a-zA-Z]{4,}', text.lower()))
    query = ' OR '.join('"' + word + '"' for word, _ in tokens.most_common(24))
    with connect(path) as db:
        rows = db.execute('SELECT text,title,source FROM samples WHERE samples MATCH ? ORDER BY bm25(samples) LIMIT ?',
                          (query, limit)).fetchall() if query else []
        if not rows:
            rows = db.execute('SELECT text,title,source FROM samples LIMIT ?', (limit,)).fetchall()
        return [dict(r) for r in rows]
