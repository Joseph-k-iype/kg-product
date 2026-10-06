from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field
from typing import Literal
from dataclasses import asdict
from app.db import get_session
from app.features.retrieval import service
from app.features.retrieval.models import EvaluationCase
from app.features.products.service import revision,touch
router=APIRouter(prefix='/api')
class RetrievalInput(BaseModel):
    query:str=Field(min_length=1,max_length=2000)
    preview:bool=False
    revision_id:str|None=None
    release_id:str|None=None
    model:dict|None=None
    mode:Literal['vector','graph','hybrid']='vector'
    limit:int=Field(5,ge=1,le=50)
@router.post('/products/{id}/retrieval')
def retrieve(id:str,input:RetrievalInput,session=Depends(get_session)):
    return service.retrieve(session,id,input)
@router.get('/products/{id}/retrieval-config')
def config(id:str,session=Depends(get_session)):
    rev=revision(session,id)
    return {'embedding_model':rev.config.get('embedding_model',asdict(service.default_model())),'limit':rev.config.get('limit',5)}
class ConfigInput(BaseModel):
    expected_generation:int
    limit:int=Field(5,ge=1,le=50)
@router.put('/products/{id}/retrieval-config')
def update(id:str,input:ConfigInput,session=Depends(get_session)):
    rev=revision(session,id,lock=True);touch(session,rev,'Search settings updated',input.expected_generation)
    rev.config={**rev.config,'limit':input.limit,'embedding_model':asdict(service.default_model())}
    return rev.config
class CaseInput(BaseModel):
    query:str=Field(min_length=1)
    expected_document_ids:list[str]=[]
@router.post('/products/{id}/evaluation-cases')
def save_case(id:str,input:CaseInput,session=Depends(get_session)):
    revision(session,id)
    case=EvaluationCase(product_id=id,**input.model_dump());session.add(case);session.flush();return {'id':case.id,'query':case.query}
