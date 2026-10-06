from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.worker import run_once
client=TestClient(app)

def prepared(name='Complaints'):
    p=client.post('/api/products',json={'name':name}).json();pid=p['id']
    ttl=Path('../fixtures/ontology/complaints.ttl').read_text()
    assert client.post(f'/api/products/{pid}/ontology/import',json={'turtle':ttl,'mode':'merge'}).status_code==200
    mapping={'classes':[{'iri':'https://knowledge.example/Complaint','label':'Complaint'},{'iri':'https://knowledge.example/Customer','label':'Customer'}],'properties':[{'iri':'https://knowledge.example/identifier','key':'identifier','kind':'datatype'},{'iri':'https://knowledge.example/submittedBy','key':'SUBMITTED_BY','kind':'object'}]}
    assert client.put(f'/api/products/{pid}/ontology/mapping',json=mapping).status_code==200
    d=client.post(f'/api/products/{pid}/documents',files={'file':('complaint.txt',b'Complaint C-1042 submitted by Customer A-203. Refund requested.','text/plain')}).json()
    run_once('test');run_once('test')
    return p,d

def test_real_falkordb_build_neighborhood_evidence_and_retry():
    p,d=prepared()
    response=client.post(f"/api/products/{p['id']}/graph/build")
    assert response.status_code==200
    first=response.json()
    assert first['state']=='ready'
    results=client.get(f"/api/products/{p['id']}/entities?q=C-1042").json()['items']
    assert results[0]['id']=='C-1042'
    assert results[0]['evidence'][0]['document_id']==d['id']
    neighbors=client.get(f"/api/products/{p['id']}/entities/C-1042/neighbors?limit=2").json()
    assert len(neighbors['nodes'])<=2
    assert neighbors['relationships'][0]['type']=='SUBMITTED_BY'
    assert client.post(f"/api/products/{p['id']}/graph/build").json()['id']==first['id']
    assert client.post(f"/api/products/{p['id']}/entities/C-1042/flags",json={'reason':'Wrong customer'}).status_code==201

def test_build_requires_valid_mapping_and_queries_do_not_cross_products():
    p,d=prepared();client.post(f"/api/products/{p['id']}/graph/build")
    other=client.post('/api/products',json={'name':'Other'}).json()
    assert client.post(f"/api/products/{other['id']}/graph/build").status_code==409
    assert client.get(f"/api/products/{other['id']}/entities?q=C-1042").status_code==409
    result=client.post(f"/api/products/{p['id']}/retrieval",json={'query':'C-1042','mode':'graph','preview':True}).json()
    assert result['results'][0]['entity']['id']=='C-1042'
