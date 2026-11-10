import json
import sqlite3
from pathlib import Path
import pytest
from scholarstyle.storage import Library, connect, load_profile
from scholarstyle.training import style_samples
from scholarstyle.llm import Ollama


class Model:
    model = 'test:7b'
    identity = 'test:7b@digest1'
    def __init__(self): self.calls = 0
    def style_identity(self): return self.identity
    def chat(self,system,payload):
        self.calls += 1
        assert 'prior_rules' not in payload
        assert len(payload['paper_excerpts']) <= 2700
        return {'rules':['Use precise terminology.','Qualify causal interpretations.']}


@pytest.fixture
def library(tmp_path):
    lib = Library(tmp_path)
    with connect(lib.path) as db:
        for i in range(3):
            text = ' '.join(f'Paper {i} section {n} examines neuronal network maturation using a carefully controlled experimental design.' for n in range(1500))
            db.execute('INSERT INTO papers VALUES (?,?,?,?,?)',(str(i),f'Paper {i}','test',text,'now'))
    return lib


def train(lib,model,cancelled=lambda:False,mode='fast'):
    return lib.train([p['id'] for p in lib.papers()],'Team',model,lambda s:None,cancelled,mode=mode)


def test_one_call_per_paper_full_text_index_and_cache(library):
    model = Model()
    profile = train(library,model)
    assert model.calls == 3
    assert profile['chunks'] > 100
    with connect(library.path) as corpus, connect(library.root/'frozen_style.sqlite') as frozen:
        assert corpus.execute('select sum(length(text)) from papers').fetchone()[0] == frozen.execute('select sum(length(text)) from samples').fetchone()[0]
    assert profile['training']['llm_calls'] == 3
    assert len(profile['paper_rules']) == 3
    second = train(library,model)
    assert model.calls == 3
    assert second['training']['cache_hits'] == 3
    assert second['training']['llm_calls'] == 0
    assert second['rules'] == profile['rules']


def test_model_digest_invalidates_cache(library):
    model = Model();train(library,model)
    model.identity = 'test:7b@new-digest'
    profile = train(library,model)
    assert model.calls == 6
    assert profile['training']['cache_hits'] == 0


def test_add_paper_reuses_previous_analysis(library):
    model=Model();train(library,model)
    with connect(library.path) as db:
        db.execute('INSERT INTO papers VALUES (?,?,?,?,?)',('new','New paper','test','We assessed activity in neuronal cultures using multielectrode arrays. '*30,'now'))
    profile=train(library,model)
    assert model.calls == 4
    assert profile['training']['cache_hits'] == 3
    assert len(profile['papers']) == 4


def test_cancel_resume_keeps_completed_samples_and_old_snapshot(library):
    train(library,None)
    path=library.root/'frozen_style.sqlite';before=path.read_bytes()
    model=Model()
    with pytest.raises(InterruptedError):
        train(library,model,lambda:model.calls >= 1)
    assert path.read_bytes() == before
    assert model.calls == 1
    result=train(library,model)
    assert model.calls == 3
    assert result['training']['cache_hits'] == 1
    assert not list(library.root.glob('training-*'))


def test_detailed_is_bounded_and_references_not_sampled():
    text='\n\n'.join(f'Paragraph {n} discusses a different aspect of scientific writing with careful attention to terminology and argumentation.' for n in range(100))
    text+='\nReferences\nREFERENCE_ONLY '*100
    fast=style_samples(text)
    detailed=style_samples(text,'detailed')
    assert len(fast)==1 and len(fast[0])<=2700
    assert 1<=len(detailed)<=3 and all(len(s)<=1800 for s in detailed)
    assert all('REFERENCE_ONLY' not in s for s in fast+detailed)


def test_corrupt_cache_recomputed(library):
    model=Model();train(library,model)
    with connect(library.root/'training_cache.sqlite') as db:
        db.execute("UPDATE style_cache SET rules='broken json'")
    result=train(library,model)
    assert model.calls==6 and result['training']['cache_hits']==0


class Response:
    def __init__(self,values):self.values=values;self.closed=False
    def __enter__(self):return self
    def __exit__(self,*args):self.closed=True
    def raise_for_status(self):pass
    def iter_lines(self,chunk_size):
        assert chunk_size==1
        for value in self.values:yield json.dumps(value).encode()


def test_training_stream_budget_and_validation():
    client=Ollama();requests=[]
    response=Response([{'message':{'content':'{"rules":['}},
                       {'message':{'content':'"Use precise terminology."]}'},'done':True,'done_reason':'stop'}])
    client.session.post=lambda *a,**kw:requests.append(kw) or response
    result=client.style_chat('system',{'paper_excerpts':'test'},lambda:False,lambda *a:None)
    assert result['rules'] == ['Use precise terminology.']
    assert response.closed
    assert requests[0]['json']['options']['num_ctx']==4096
    assert requests[0]['json']['options']['num_predict']==384
    assert requests[0]['json']['think'] is False
    assert requests[0]['stream'] and requests[0]['json']['stream']


def test_stream_cancel_closes_response():
    client=Ollama();calls=0
    def cancelled():
        nonlocal calls
        calls+=1
        return calls>1
    response=Response([{'message':{'content':'{'}}])
    client.session.post=lambda *a,**kw:response
    with pytest.raises(InterruptedError):
        client.style_chat('system',{},cancelled,lambda *a:None)
    assert response.closed


@pytest.mark.parametrize('ending',[{'done':True,'done_reason':'length'},{}])
def test_stream_truncation_is_not_cached(ending):
    client=Ollama();response=Response([{'message':{'content':'{"rules":["x"]}'},**ending}])
    client.session.post=lambda *a,**kw:response
    with pytest.raises(ValueError):client.style_chat('system',{},lambda:False,lambda *a:None)
