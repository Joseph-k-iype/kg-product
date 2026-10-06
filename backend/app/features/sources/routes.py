from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.db import get_session
from app.features.sources.models import Source
from app.features.products.models import Product, now
from app.features.products.service import require
from app.features.documents.service import upload_document
from app.adapters.sources import config_check, read_source
from app.features.products.service import revision, mutable

router = APIRouter(prefix="/api")


class SourceInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str = "local"
    owner: str = "Demo author"
    location: str = ""
    freshness_days: int = Field(30, ge=1, le=3650)
    product_ids: list[str] = []
    config: dict = {}


@router.get("/sources")
def sources(session=Depends(get_session, scope="function")):
    return session.scalars(select(Source).order_by(Source.name)).all()


@router.post("/sources", status_code=201)
def create(input: SourceInput, session=Depends(get_session, scope="function")):
    if input.type not in ("local", "external", "fixture", "postgres", "api", "cloud", "business", "other"):
        raise HTTPException(422, "Choose a supported source type")
    try:
        config_check(input.type, input.config, input.location)
    except ValueError as error:
        raise HTTPException(422, str(error))
    for id in input.product_ids:
        require(session, Product, id)
    source = Source(
        **input.model_dump(), connection_state="local_upload" if input.type == "local" else "registered"
    )
    session.add(source)
    session.flush()
    return source


@router.post("/sources/{id}/test")
def test_connection(id: str, session=Depends(get_session, scope="function")):
    source = require(session, Source, id)
    try:
        result = read_source(source)
    except ValueError as error:
        raise HTTPException(422, str(error))
    return result["preview"]


@router.post("/sources/test")
def test_unsaved(input: SourceInput):
    source = Source(**input.model_dump())
    try:
        return read_source(source)["preview"]
    except ValueError as error:
        raise HTTPException(422, str(error))


@router.post("/sources/{id}/sync")
def import_snapshot(id: str, session=Depends(get_session, scope="function")):
    source = session.scalars(select(Source).where(Source.id == id).with_for_update()).first()
    if not source:
        raise HTTPException(404, "Source not found")
    if not source.product_ids:
        raise HTTPException(422, "Associate a product draft before importing records.")
    revisions = [revision(session, pid, lock=True) for pid in sorted(source.product_ids)]
    for rev in revisions:
        mutable(rev)
    try:
        result = read_source(source)
    except ValueError as error:
        raise HTTPException(422, str(error))
    from app.features.sources.service import save_snapshot

    documents = [save_snapshot(session, rev, source, result) for rev in revisions]
    source.connection_state = "connected"
    source.last_synced_at = now()
    return {"documents": documents, **result["preview"], "label": "Imported read-only source snapshot"}


@router.post("/sources/{id}/sync-fixture")
def sync(id: str, session=Depends(get_session, scope="function")):
    source = require(session, Source, id)
    documents = []
    for pid in source.product_ids:
        d = upload_document(
            session,
            pid,
            source.name + "-demo.txt",
            b"Complaint C-1042 submitted by Customer A-203. Refund requested.\nComplaint C-1043 submitted by Customer A-204. Delivery delayed.",
            "text/plain",
            source_id=source.id,
        )
        documents.append(d["id"])
    source.last_synced_at = now()
    source.connection_state = "fixture_synced"
    return {"label": "Fixture synchronization", "documents": documents}
