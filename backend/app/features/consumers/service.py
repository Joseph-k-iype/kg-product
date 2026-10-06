from sqlalchemy import select
from fastapi import HTTPException
from app.features.products.models import Product
from app.features.products.service import require
from app.features.releases.models import Release
from app.features.consumers.models import Consumer

def resolve_consumer(session,consumer):
    if isinstance(consumer,str):consumer=require(session,Consumer,consumer)
    product=require(session,Product,consumer.product_id)
    id=consumer.release_id if consumer.release_policy=='pinned' else product.active_release_id
    if not id:return {'release_id':None,'state':'awaiting_publication'}
    release=require(session,Release,id)
    return {'release_id':release.id,'number':release.number,'product_id':release.product_id,'revision_id':release.revision_id,'state':'ready'}

def consumer_detail(session,consumer):
    return {'id':consumer.id,'name':consumer.name,'type':consumer.type,'product_id':consumer.product_id,'product_name':require(session,Product,consumer.product_id).name,'release_policy':consumer.release_policy,'release_id':consumer.release_id,'usage':consumer.usage,'resolved':resolve_consumer(session,consumer)}

def save_consumer(session,input,id=None):
    require(session,Product,input.product_id)
    if input.release_policy=='pinned':
        if not input.release_id:raise HTTPException(422,'Select a published release to pin')
        release=require(session,Release,input.release_id)
        if release.product_id!=input.product_id:raise HTTPException(422,'Release belongs to a different product')
    values=input.model_dump();values['release_id']=input.release_id if input.release_policy=='pinned' else None
    consumer=require(session,Consumer,id) if id else Consumer(**values)
    if id:
        for k,v in values.items():setattr(consumer,k,v)
    else:session.add(consumer)
    session.flush();return consumer_detail(session,consumer)
