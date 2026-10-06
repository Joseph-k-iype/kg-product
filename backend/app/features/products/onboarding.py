from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.sources import read_source
from app.adapters.structured import preview
from app.db import get_session
from app.features.documents.service import upload_document
from app.features.ontology.routes import StarterInput, starter
from app.features.products import service
from app.features.products.models import Product, now
from app.features.products.schemas import ProductCreate
from app.features.sources.models import Source
from app.features.sources.routes import SourceInput
from app.features.sources.routes import create as create_source

router = APIRouter(prefix="/api")


class OnboardingInput(ProductCreate):
    template: Literal["general", "customer-support", "empty"] = "general"
    existing_source_id: str | None = None
    source: SourceInput | None = None
    import_source_now: bool = False


@router.post("/onboarding", status_code=201)
async def onboard(
    metadata: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session, scope="function")],
    files: Annotated[list[UploadFile] | None, File()] = None,
):
    files = files or []
    try:
        input = OnboardingInput.model_validate_json(metadata)
    except (ValidationError, ValueError):
        raise HTTPException(422, "Check the product and source details before creating the draft.")
    if input.source and input.existing_source_id:
        raise HTTPException(422, "Choose an existing source or a new source, not both.")
    if len(files) > 20:
        raise HTTPException(422, "Import at most 20 files at a time.")
    uploads = []
    total = 0
    for file in files:
        data = await file.read(20 * 1024 * 1024 + 1)
        total += len(data)
        if total > 100 * 1024 * 1024:
            raise HTTPException(413, "Use at most 100 MB of files per draft.")
        try:
            preview(file.filename or "document.txt", data)
        except ValueError as error:
            raise HTTPException(422, {"code": "invalid_import", "message": f"{file.filename}: {error}"})
        uploads.append(
            (file.filename or "document.txt", data, file.content_type or "application/octet-stream")
        )
    product = service.create_product(
        session, ProductCreate(**input.model_dump(include=set(ProductCreate.model_fields)))
    )
    pid = product["id"]
    if input.template != "empty":
        starter(pid, StarterInput(template=input.template), session=session)
    source = None
    if input.existing_source_id:
        source = session.scalars(
            select(Source).where(Source.id == input.existing_source_id).with_for_update()
        ).first()
        if not source:
            raise HTTPException(404, "Source not found")
        source.product_ids = list(dict.fromkeys([*source.product_ids, pid]))
    elif input.source:
        source = create_source(input.source.model_copy(update={"product_ids": [pid]}), session)
    for name, data, content_type in uploads:
        upload_document(session, pid, name, data, content_type)
    if input.import_source_now:
        if not source:
            raise HTTPException(422, "Choose a database or API source before importing its records.")
        try:
            snapshot = read_source(source)
        except ValueError as error:
            raise HTTPException(422, str(error))
        from app.features.sources.service import save_snapshot

        save_snapshot(session, service.revision(session, pid), source, snapshot)
        source.connection_state, source.last_synced_at = "connected", now()
    return service.detail(session, service.require(session, Product, pid))
