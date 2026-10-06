from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select
from app.domain.contracts import ArtifactRef
from app.features.products.service import revision, require, touch
from app.features.documents.models import Document, Chunk
from app.features.processing.models import Job
from app.adapters.storage import ObjectStore

MIME_TYPES = {
    ".txt": "text/plain",
    ".md": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".ttl": "text/turtle",
    ".turtle": "text/turtle",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

STAGES = ["uploaded", "extracted", "chunked", "embedded", "graph_built", "validated"]


def enqueue_stage(session, rev, document, stage):
    fingerprint = document.sha256 + "/" + document.processing_version
    job = session.scalars(
        select(Job).where(Job.document_id == document.id, Job.stage == stage, Job.input_hash == fingerprint)
    ).first()
    if not job:
        job = Job(
            product_id=rev.product_id,
            revision_id=rev.id,
            document_id=document.id,
            stage=stage,
            input_hash=fingerprint,
        )
        session.add(job)
        session.flush()
    return job


def upload_document(
    session, product_id, name, data, content_type, revision_id=None, source_id=None, normalized_data=None
):
    if not data:
        raise HTTPException(422, {"code": "empty_file", "message": "Choose a file with content."})
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(
            413, {"code": "file_too_large", "message": "Choose a document smaller than 20 MB."}
        )
    from app.adapters.structured import preview, parse

    try:
        if normalized_data is None:
            preview(name, data)
            structured = parse(name, data)
        else:
            structured = normalized_data
    except ValueError as error:
        raise HTTPException(422, {"code": "invalid_import", "message": str(error)})
    content_type = MIME_TYPES[Path(name).suffix.lower()]
    rev = revision(session, product_id, revision_id, lock=True)
    if source_id:
        from app.features.sources.models import Source

        source = require(session, Source, source_id)
        if product_id not in source.product_ids:
            raise HTTPException(422, "Source is not associated with this product")
    touch(session, rev, "Document added")
    if structured["kind"] == "turtle":
        from app.features.products.models import uid
        structured = {**structured, "blank_scope": uid()}
    if structured.get("definitions"):
        from app.features.documents.imports import prepare_definitions

        prepare_definitions(session, rev, structured)
    artifact = ObjectStore().put(data, content_type)
    doc = Document(
        product_id=product_id,
        revision_id=rev.id,
        source_id=source_id,
        name=Path(name).name,
        data_kind=structured["kind"],
        structured_data=structured if structured["kind"] != "document" else {},
        content_type=content_type,
        object_key=artifact.key,
        sha256=artifact.sha256,
        size=len(data),
    )
    session.add(doc)
    session.flush()
    if doc.data_kind == "definitions":
        doc.extracted_text = structured["definitions"]
        extracted = ObjectStore().put(doc.extracted_text.encode(), "text/plain")
        doc.extracted_key, doc.extracted_sha256 = extracted.key, extracted.sha256
        doc.state = "definitions_ready"
    else:
        if doc.data_kind != "document":
            doc.processing_version = "structured-v1/record-v1"
        enqueue_stage(session, rev, doc, "extracted")
    return document_detail(session, doc)


def document_detail(session, doc):
    chunks = session.scalars(select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.ordinal)).all()
    jobs = session.scalars(select(Job).where(Job.document_id == doc.id).order_by(Job.created_at)).all()
    return {
        "id": doc.id,
        "name": doc.name,
        "data_kind": doc.data_kind,
        "active": doc.active,
        "record_count": len(doc.structured_data.get("records", [])),
        "product_id": doc.product_id,
        "revision_id": doc.revision_id,
        "source_id": doc.source_id,
        "content_type": doc.content_type,
        "object_key": doc.object_key,
        "sha256": doc.sha256,
        "size": doc.size,
        "state": doc.state,
        "processing_version": doc.processing_version,
        "uploaded_at": doc.uploaded_at,
        "uploaded_by": doc.uploaded_by,
        "extracted_text": doc.extracted_text,
        "chunks": [
            {
                "id": c.id,
                "text": c.text,
                "start": c.start,
                "end": c.end,
                "ordinal": c.ordinal,
                "embedded": c.embedding is not None,
                "model_name": c.model_name,
                "model_revision": c.model_revision,
            }
            for c in chunks
        ],
        "jobs": [
            {
                "id": j.id,
                "stage": j.stage,
                "state": j.state,
                "attempt_count": j.attempt_count,
                "attempts": j.attempts,
                "error": j.error,
            }
            for j in jobs
        ],
    }


def retry_job(session, id):
    job = require(session, Job, id)
    rev = revision(session, job.product_id, job.revision_id, lock=True)
    from app.features.products.service import mutable

    mutable(rev)
    if job.state != "failed":
        raise HTTPException(409, {"code": "retry_failed_only", "message": "Only failed work can be retried."})
    job.state = "queued"
    job.error = None
    return {"id": job.id, "state": job.state}
