from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.db import get_session
from app.features.products.service import revision
from app.features.evaluations import service
from app.features.evaluations.models import EvaluationRun

router = APIRouter(prefix="/api/products/{id}/evaluations")


@router.post("")
def evaluate(id: str, revision_id: str | None = None, session=Depends(get_session, scope="function")):
    return service.evaluate(session, revision(session, id, revision_id, lock=True))


@router.get("")
def runs(id: str, revision_id: str | None = None, session=Depends(get_session, scope="function")):
    rev = revision(session, id, revision_id)
    return [
        service.run_detail(session, r, rev)
        for r in session.scalars(
            select(EvaluationRun)
            .where(EvaluationRun.revision_id == rev.id)
            .order_by(EvaluationRun.created_at.desc())
        )
    ]
