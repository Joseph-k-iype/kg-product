from fastapi.testclient import TestClient
from app.main import app
from app.worker import run_once
from app.db import SessionLocal
from app.features.documents.models import Chunk
from app.features.retrieval.service import store_embedding
from app.domain.contracts import ModelRef
client=TestClient(app)

def create_chunks(name,text):
    p=client.post('/api/products',json={'name':name}).json()
    d=client.post(f"/api/products/{p['id']}/documents",files={'file':('evidence.txt',text.encode(),'text/plain')}).json()
    run_once('test');run_once('test')
    return p,d

def test_dimension_and_model_compatibility_are_enforced():
    p,d=create_chunks('Vector test','A refund is available within 30 days.')
    with SessionLocal() as s:
        c=s.query(Chunk).first()
        from pytest import raises
        with raises(ValueError):store_embedding(c,[1.0]*8,ModelRef('test','revision-a',384))
        store_embedding(c,[1.0]+[0.0]*383,ModelRef('test','revision-a',384));s.commit()
    result=client.post(f"/api/products/{p['id']}/retrieval",json={'query':'refund','preview':True,'model':{'name':'test','revision':'revision-b','dimension':384}})
    assert result.status_code==409

def test_vector_search_isolates_products_and_cites_correct_excerpt(monkeypatch):
    p,d=create_chunks('Refunds','A refund is available within 30 days.')
    other,_=create_chunks('Private','Private customer record.')
    from app.features.retrieval import service
    class Provider:
        def embed(self,texts,model):
            assert model.dimension==384
            return [[1.0]+[0.0]*383 for text in texts]
    monkeypatch.setattr(service,'provider',Provider())
    with SessionLocal() as s:
        for c in s.query(Chunk):store_embedding(c,[1.0]+[0.0]*383,service.default_model())
        s.commit()
    hits=client.post(f"/api/products/{p['id']}/retrieval",json={'query':'refund','preview':True}).json()['results']
    assert len(hits)==1
    assert hits[0]['evidence']['document_id']==d['id']
    assert hits[0]['evidence']['text']=='A refund is available within 30 days.'
    assert hits[0]['evidence']['source_url']==f"/api/documents/{d['id']}/original"

def test_unavailable_provider_returns_actionable_error(monkeypatch):
    p,d=create_chunks('Unavailable','Evidence')
    from app.features.retrieval import service
    with SessionLocal() as s:
        store_embedding(s.query(Chunk).first(),[1.0]+[0.0]*383,service.default_model());s.commit()
    class FailedProvider:
        def embed(self,texts,model):raise RuntimeError('Download the configured model')
    monkeypatch.setattr(service,'provider',FailedProvider())
    result=client.post(f"/api/products/{p['id']}/retrieval",json={'query':'Evidence','preview':True})
    assert result.status_code==503
    assert result.json()['detail']['code']=='embedding_provider_unavailable'
