from fastapi import APIRouter, Depends
from app.db import get_session
from app.features.lineage.service import lineage

router = APIRouter(prefix="/api")


@router.get("/products/{id}/lineage")
def get(id: str, release_id: str | None = None, revision_id: str | None = None, session=Depends(get_session, scope="function")):
    return lineage(session, id, release_id, revision_id)
