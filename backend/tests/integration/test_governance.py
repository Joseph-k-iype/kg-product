from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.features.documents.models import Chunk
from app.features.retrieval.service import store_embedding,default_model
from tests.integration.test_graph import prepared
client=TestClient(app)
def ready():
    p,d=prepared();pid=p['id']
    detail=client.get(f'/api/products/{pid}').json()
    client.patch(f'/api/products/{pid}',json={'expected_generation':detail['draft']['generation'],'purpose':'Trusted customer support'})
    with SessionLocal() as s:
        for c in s.query(Chunk):store_embedding(c,[1.0]+[0.0]*383,default_model())
        s.commit()
    assert client.post(f'/api/products/{pid}/graph/build').status_code==200
    return p,d

def approve(pid):
    checks=client.post(f'/api/products/{pid}/evaluations')
    assert checks.status_code==200
    assert checks.json()['state']=='passed'
    review=client.post(f'/api/products/{pid}/reviews',json={'summary':'Ready for customer support'}).json()
    assert client.post(f"/api/reviews/{review['id']}/decision",json={'decision':'approve','reason':'Evidence verified','reviewer_id':'demo-reviewer'}).status_code==200
    return review

def test_missing_inputs_and_stale_approval_are_blocked():
    p=client.post('/api/products',json={'name':'Empty'}).json()
    assert client.post(f"/api/products/{p['id']}/evaluations").json()['state']=='insufficient_data'
    p,d=ready();pid=p['id'];review=approve(pid)
    detail=client.get(f'/api/products/{pid}').json()
    client.patch(f'/api/products/{pid}',json={'expected_generation':detail['draft']['generation'],'purpose':'Changed purpose'})
    assert client.get(f'/api/products/{pid}/evaluations').json()[0]['state']=='stale'
    assert client.get('/api/reviews').json()[0]['state']=='superseded'
    assert client.post(f'/api/products/{pid}/releases').status_code==409

def test_failed_preparation_preserves_release_and_published_snapshot(monkeypatch):
    p,d=ready();pid=p['id'];approve(pid)
    published=client.post(f'/api/products/{pid}/releases')
    assert published.status_code==201
    old=published.json()
    assert old['manifest']['chunk_ids']
    draft=client.post(f'/api/products/{pid}/draft').json()
    assert draft['draft']['id']!=old['revision_id']
    copied=client.get(f'/api/products/{pid}/documents').json()
    assert len(copied)==1
    assert copied[0]['id']!=d['id']
    client.post(f'/api/products/{pid}/graph/build');approve(pid)
    from app.features.releases import service
    def fail(*args):raise RuntimeError('Storage unavailable')
    monkeypatch.setattr(service.store,'verify',fail)
    assert client.post(f'/api/products/{pid}/releases').status_code==503
    assert client.get(f'/api/products/{pid}').json()['active_release_id']==old['id']
    assert client.get(f"/api/products/{pid}/releases/{old['id']}").json()['manifest']['document_ids']==[d['id']]

def test_published_revision_cannot_be_edited():
    p,d=ready();pid=p['id'];approve(pid)
    release=client.post(f'/api/products/{pid}/releases').json()
    response=client.patch(f"/api/products/{pid}/ontology?revision_id={release['revision_id']}",json={'kind':'class','iri':'https://knowledge.example/Unsafe','label':'Unsafe'})
    assert response.status_code==409
