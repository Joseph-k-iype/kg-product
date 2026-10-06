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


def upload_document(session, product_id, name, data, content_type, revision_id=None, source_id=None):
    if not data:
        raise HTTPException(422, {"code": "empty_file", "message": "Choose a file with content."})
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(
            413, {"code": "file_too_large", "message": "Choose a document smaller than 20 MB."}
        )
    if Path(name).suffix.lower() not in (".txt", ".pdf", ".docx", ".md"):
        raise HTTPException(422, {"code": "unsupported_file", "message": "Use a text, PDF or Word document."})
    content_type = MIME_TYPES[Path(name).suffix.lower()]
    rev = revision(session, product_id, revision_id, lock=True)
    if source_id:
        from app.features.sources.models import Source

        source = require(session, Source, source_id)
        if product_id not in source.product_ids:
            raise HTTPException(422, "Source is not associated with this product")
    touch(session, rev, "Document added")
    artifact = ObjectStore().put(data, content_type)
    doc = Document(
        product_id=product_id,
        revision_id=rev.id,
        source_id=source_id,
        name=Path(name).name,
        content_type=content_type,
        object_key=artifact.key,
        sha256=artifact.sha256,
        size=len(data),
    )
    session.add(doc)
    session.flush()
    enqueue_stage(session, rev, doc, "extracted")
    return document_detail(session, doc)


def document_detail(session, doc):
    chunks = session.scalars(select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.ordinal)).all()
    jobs = session.scalars(select(Job).where(Job.document_id == doc.id).order_by(Job.created_at)).all()
    return {
        "id": doc.id,
        "name": doc.name,
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
