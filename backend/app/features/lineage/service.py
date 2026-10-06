from sqlalchemy import select
from fastapi import HTTPException
from app.features.products.models import Product
from app.features.products.service import require,revision
from app.features.releases.models import Release
from app.features.evaluations.service import snapshot
from app.features.consumers.models import Consumer
from app.features.consumers.service import resolve_consumer

def lineage(session,product_id,release_id=None,revision_id=None):
    product=require(session,Product,product_id)
    release=session.get(Release,release_id or product.active_release_id) if release_id or (product.active_release_id and not revision_id) else None
    if release and release.product_id!=product_id:raise HTTPException(404,'Release not found')
    rev=revision(session,product_id,release.revision_id if release else revision_id)
    inputs=release.manifest if release else snapshot(session,rev)
    nodes={};edges=[]
    def node(id,type,label,record_id=None,**metadata):nodes[id]={'id':id,'type':type,'label':label,'record_id':record_id or id,**metadata}
    def edge(a,b,label):edges.append({'source':a,'target':b,'label':label})
    for d in inputs['documents']:
        source=d['source_id'] or 'upload-'+d['id'];node(source,'source','Source document',d['source_id'],provenance='Local upload' if not d['source_id'] else 'Registered source')
        node(d['id'],'document','Original document',d['id'],sha256=d['sha256'],object_key=d['object_key']);edge(source,d['id'],'uploaded')
        extracted='extracted-'+d['id'];node(extracted,'extracted','Readable text',d['id'],sha256=d['extracted_sha256']);edge(d['id'],extracted,'extracted')
        for c in (c for c in inputs['chunks'] if c['document_id']==d['id']):
            node(c['id'],'chunk','Evidence excerpt',c['id'],document_id=d['id'],start=c['start'],end=c['end']);edge(extracted,c['id'],'split into excerpts')
            if c['embedded']:
                e='embedding-'+c['id'];node(e,'embedding','Searchable evidence',c['id'],model=c['model_name'],model_revision=c['model_revision'],dimension=c['model_dimension']);edge(c['id'],e,'prepared for search')
                if release:edge(e,release.id,'included in release')
            if inputs['graph_build_id']:edge(c['id'],inputs['graph_build_id'],'supports facts')
    if inputs['ontology_id']:node(inputs['ontology_id'],'ontology','Concept definitions',inputs['ontology_id'],sha256=inputs['ontology_sha256'])
    if inputs['mapping_id']:node(inputs['mapping_id'],'mapping','Representation settings',inputs['mapping_id'])
    if inputs['graph_build_id']:
        node(inputs['graph_build_id'],'graph','Prepared facts',inputs['graph_build_id'],state='ready',ontology_id=inputs['ontology_id'],mapping_id=inputs['mapping_id'])
        for id in [inputs['ontology_id'],inputs['mapping_id']]:
            if id:edge(id,inputs['graph_build_id'],'defines representation')
        if release:edge(inputs['graph_build_id'],release.id,'included in release')
    if release:
        node(release.id,'release',f'Release {release.number}',release.id,state='published',revision_id=rev.id)
        for c in session.scalars(select(Consumer).where(Consumer.product_id==product_id)):
            if resolve_consumer(session,c)['release_id']==release.id:
                node(c.id,'consumer',c.name,c.id,policy=c.release_policy);edge(release.id,c.id,'consumed by')
    return {'nodes':list(nodes.values()),'edges':edges,'revision_id':rev.id,'release_id':release.id if release else None,'label':'Published evidence trail' if release else 'Draft evidence trail'}
