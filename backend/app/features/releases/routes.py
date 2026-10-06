from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.db import get_session
from app.features.products.service import revision, require
from app.features.releases import service
from app.features.releases.models import Release

router = APIRouter(prefix="/api/products/{id}/releases")


@router.post("", status_code=201)
def publish(id: str, session=Depends(get_session)):
    return service.activate_release(session, revision(session, id, lock=True))


@router.get("")
def releases(id: str, session=Depends(get_session)):
    return [
        service.release_detail(r)
        for r in session.scalars(
            select(Release).where(Release.product_id == id).order_by(Release.number.desc())
        )
    ]


@router.get("/{release_id}")
def get(id: str, release_id: str, session=Depends(get_session)):
    release = require(session, Release, release_id)
    if release.product_id != id:
        raise HTTPException(404, "Release not found for this product")
    return service.release_detail(release)
