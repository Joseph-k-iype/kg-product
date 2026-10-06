from fastapi import APIRouter,Depends,Response,HTTPException
from app.db import get_session
from app.features.products.service import revision
from app.features.ontology import service
from app.features.ontology.schemas import OntologyEdit,ImportInput,MappingInput,SampleInput
router=APIRouter(prefix='/api/products/{id}/ontology')
@router.get('')
def get(id:str,revision_id:str|None=None,session=Depends(get_session)):
    return service.details(session,revision(session,id,revision_id))
@router.patch('')
def edit(id:str,input:OntologyEdit,revision_id:str|None=None,session=Depends(get_session)):
    return service.save_ontology(session,revision(session,id,revision_id,lock=True),input)
@router.post('/import')
def import_rdf(id:str,input:ImportInput,revision_id:str|None=None,session=Depends(get_session)):
    return service.import_ontology(session,revision(session,id,revision_id,lock=True),input)
@router.get('/export')
def export(id:str,revision_id:str|None=None,session=Depends(get_session)):
    return Response(service.details(session,revision(session,id,revision_id))['turtle'],media_type='text/turtle')
@router.post('/impact')
def impact(id:str,input:ImportInput,revision_id:str|None=None,session=Depends(get_session)):
    try:return service.impact(session,revision(session,id,revision_id),input.turtle)
    except Exception as e:raise HTTPException(422,str(e))
@router.put('/mapping')
def map_rdf(id:str,input:MappingInput,revision_id:str|None=None,session=Depends(get_session)):
    return service.save_mapping(session,revision(session,id,revision_id,lock=True),input)
@router.post('/validate-sample')
def validate_sample(id:str,input:SampleInput,revision_id:str|None=None,session=Depends(get_session)):
    ontology=service.details(session,revision(session,id,revision_id))['turtle']
    try:return {'findings':service.adapter.validate(ontology,ontology,input.turtle)}
    except Exception as e:raise HTTPException(422,str(e))
