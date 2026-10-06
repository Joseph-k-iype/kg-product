import json
from dataclasses import asdict
from sqlalchemy import select,func
from fastapi import HTTPException
from app.features.products.service import require,mutable
from app.features.products.models import Product,Activity
from app.features.releases.models import Release
from app.features.reviews.models import Review
from app.features.evaluations.service import current_pass,snapshot,fingerprint
from app.features.ontology.models import OntologyVersion
from app.features.graph.models import GraphBuild
from app.adapters.storage import ObjectStore
from app.adapters.graph import GraphAdapter
from app.features.retrieval.service import default_model
store=ObjectStore()
graph=GraphAdapter()

def release_detail(release):
    return {'id':release.id,'product_id':release.product_id,'revision_id':release.revision_id,'number':release.number,'manifest':release.manifest,'published_by':release.published_by,'created_at':release.created_at}

def prepare_release(session,rev):
    mutable(rev);run=current_pass(session,rev)
    approval=session.scalars(select(Review).where(Review.revision_id==rev.id,Review.state=='approved',Review.input_hash==run.input_hash).order_by(Review.created_at.desc())).first()
    if not approval:raise HTTPException(409,{'code':'approval_required','message':'A current reviewer approval is required before publishing.'})
    inputs=snapshot(session,rev);ontology=require(session,OntologyVersion,rev.ontology_id);build=require(session,GraphBuild,rev.graph_build_id)
    if build.state!='ready' or build.ontology_id!=rev.ontology_id or build.mapping_id!=rev.mapping_id:raise HTTPException(409,'Prepare the current concepts and facts before publishing')
    try:
        for doc in inputs['documents']:
            store.verify(doc['object_key'],doc['sha256']);store.verify(doc['extracted_key'],doc['extracted_sha256'])
        store.verify(ontology.object_key,ontology.sha256);graph.verify(build)
        manifest={**inputs,'document_ids':[d['id'] for d in inputs['documents']],'chunk_ids':[c['id'] for c in inputs['chunks']],'ontology_object_key':ontology.object_key,'embedding_model':rev.config.get('embedding_model',asdict(default_model())),'evaluation_id':run.id,'review_id':approval.id,'input_hash':run.input_hash,'graph_key':build.graph_key}
        artifact=store.put(json.dumps(manifest,sort_keys=True).encode(),'application/json')
        store.verify(artifact.key,artifact.sha256)
        return manifest,artifact
    except Exception as e:raise HTTPException(503,{'code':'release_preparation_failed','message':'Publication could not be prepared. The previous release remains active. '+str(e)})

def activate_release(session,rev):
    product=session.scalars(select(Product).where(Product.id==rev.product_id).with_for_update()).one()
    manifest,artifact=prepare_release(session,rev)
    if manifest['input_hash']!=fingerprint(snapshot(session,rev)):raise HTTPException(409,'Draft changed during publication')
    number=(session.scalar(select(func.max(Release.number)).where(Release.product_id==rev.product_id)) or 0)+1
    release=Release(product_id=rev.product_id,revision_id=rev.id,number=number,manifest=manifest,object_key=artifact.key,sha256=artifact.sha256)
    session.add(release);session.flush();product.active_release_id=release.id;rev.state='published'
    session.add(Activity(product_id=rev.product_id,revision_id=rev.id,action=f'Release {number} published',detail={'release_id':release.id}))
    return release_detail(release)
