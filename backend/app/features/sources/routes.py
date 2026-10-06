from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
from app.db import get_session
from app.features.sources.models import Source
from app.features.products.models import Product,now
from app.features.products.service import require
from app.features.documents.service import upload_document
router=APIRouter(prefix='/api')
class SourceInput(BaseModel):
    name:str=Field(min_length=1,max_length=200)
    type:str='local'
    owner:str='Demo author'
    location:str=''
    freshness_days:int=Field(30,ge=1,le=3650)
    product_ids:list[str]=[]
@router.get('/sources')
def sources(session=Depends(get_session)):
    return session.scalars(select(Source).order_by(Source.name)).all()
@router.post('/sources',status_code=201)
def create(input:SourceInput,session=Depends(get_session)):
    if input.type not in ('local','external','fixture'):raise HTTPException(422,'Choose local, external or fixture')
    for id in input.product_ids:require(session,Product,id)
    source=Source(**input.model_dump(),connection_state='local_upload' if input.type=='local' else 'registered')
    session.add(source);session.flush();return source
@router.post('/sources/{id}/sync-fixture')
def sync(id:str,session=Depends(get_session)):
    source=require(session,Source,id)
    documents=[]
    for pid in source.product_ids:
        d=upload_document(session,pid,source.name+'-demo.txt',b'Complaint C-1042 submitted by Customer A-203. Refund requested.\nComplaint C-1043 submitted by Customer A-204. Delivery delayed.','text/plain',source_id=source.id)
        documents.append(d['id'])
    source.last_synced_at=now();source.connection_state='fixture_synced'
    return {'label':'Fixture synchronization','documents':documents}
