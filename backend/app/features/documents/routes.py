from fastapi import APIRouter,Depends,UploadFile,File,Response
from sqlalchemy import select
from app.db import get_session
from app.features.products.service import require,revision
from app.features.documents import service
from app.features.documents.models import Document
from app.adapters.storage import ObjectStore
from app.domain.contracts import ArtifactRef
router=APIRouter(prefix='/api')
@router.post('/products/{id}/documents',status_code=201)
async def upload(id:str,file:UploadFile=File(...),revision_id:str|None=None,source_id:str|None=None,session=Depends(get_session)):
    data=await file.read(20*1024*1024+1)
    return service.upload_document(session,id,file.filename or 'document.txt',data,file.content_type or 'application/octet-stream',revision_id,source_id)
@router.get('/products/{id}/documents')
def documents(id:str,revision_id:str|None=None,session=Depends(get_session)):
    rev=revision(session,id,revision_id)
    return [service.document_detail(session,d) for d in session.scalars(select(Document).where(Document.revision_id==rev.id).order_by(Document.uploaded_at.desc()))]
@router.get('/documents/{id}')
def document(id:str,session=Depends(get_session)):
    return service.document_detail(session,require(session,Document,id))
@router.get('/documents/{id}/original')
def original(id:str,session=Depends(get_session)):
    d=require(session,Document,id)
    data=ObjectStore().get(ArtifactRef(d.object_key,d.sha256,d.sha256))
    return Response(data,media_type=d.content_type,headers={'Content-Disposition':"inline; filename*=UTF-8''"+__import__('urllib.parse',fromlist=['quote']).quote(d.name)})
@router.post('/jobs/{id}/retry')
def retry(id:str,session=Depends(get_session)):
    return service.retry_job(session,id)
@router.get('/products/{id}/processing')
def processing(id:str,revision_id:str|None=None,session=Depends(get_session)):
    rev=revision(session,id,revision_id)
    docs=session.scalars(select(Document).where(Document.revision_id==rev.id)).all()
    return {'revision_id':rev.id,'generation':rev.generation,'stages':service.STAGES,'documents':[service.document_detail(session,d) for d in docs]}
