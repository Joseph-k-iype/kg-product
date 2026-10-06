from fastapi import APIRouter,Depends
from app.db import get_session
from app.features.overview.service import overview
router=APIRouter(prefix='/api')
@router.get('/overview')
def get(session=Depends(get_session)):
    return overview(session)
