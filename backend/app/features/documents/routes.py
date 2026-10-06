from fastapi import APIRouter, Depends, UploadFile, File, Response
from sqlalchemy import select
from app.db import get_session
from app.features.products.service import require, revision
from app.features.documents import service
from app.features.documents.models import Document
from app.adapters.storage import ObjectStore
from app.domain.contracts import ArtifactRef

router = APIRouter(prefix="/api")


@router.post("/products/{id}/documents", status_code=201)
async def upload(
    id: str,
    file: UploadFile = File(...),
    revision_id: str | None = None,
    source_id: str | None = None,
    session=Depends(get_session),
):
    data = await file.read(20 * 1024 * 1024 + 1)
    return service.upload_document(
        session,
        id,
        file.filename or "document.txt",
        data,
        file.content_type or "application/octet-stream",
        revision_id,
        source_id,
    )


@router.get("/products/{id}/documents")
def documents(id: str, revision_id: str | None = None, session=Depends(get_session)):
    rev = revision(session, id, revision_id)
    return [
        service.document_detail(session, d)
        for d in session.scalars(
            select(Document).where(Document.revision_id == rev.id).order_by(Document.uploaded_at.desc())
        )
    ]


@router.get("/documents/{id}")
def document(id: str, session=Depends(get_session)):
    return service.document_detail(session, require(session, Document, id))


@router.get("/documents/{id}/original")
def original(id: str, session=Depends(get_session)):
    d = require(session, Document, id)
    data = ObjectStore().get(ArtifactRef(d.object_key, d.sha256, d.sha256))
    return Response(
        data,
        media_type=service.MIME_TYPES.get(
            __import__("pathlib").Path(d.name).suffix.lower(), "application/octet-stream"
        ),
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
            "Content-Disposition": "inline; filename*=UTF-8''"
            + __import__("urllib.parse", fromlist=["quote"]).quote(d.name),
        },
    )


@router.post("/jobs/{id}/retry")
def retry(id: str, session=Depends(get_session)):
    return service.retry_job(session, id)


@router.get("/products/{id}/processing")
def processing(id: str, revision_id: str | None = None, session=Depends(get_session)):
    rev = revision(session, id, revision_id)
    docs = session.scalars(select(Document).where(Document.revision_id == rev.id)).all()
    from app.features.processing.models import Job

    revision_jobs = session.scalars(
        select(Job).where(Job.revision_id == rev.id, Job.document_id.is_(None)).order_by(Job.created_at)
    ).all()
    return {
        "revision_id": rev.id,
        "generation": rev.generation,
        "stages": service.STAGES,
        "documents": [service.document_detail(session, d) for d in docs],
        "revision_jobs": [
            {
                "id": j.id,
                "stage": j.stage,
                "state": j.state,
                "attempt_count": j.attempt_count,
                "attempts": j.attempts,
                "error": j.error,
            }
            for j in revision_jobs
        ],
    }


@router.post("/products/{id}/processing/run")
def prepare(id: str, revision_id: str | None = None, session=Depends(get_session)):
    from app.features.products.service import mutable
    from app.features.processing.models import Job
    from app.features.graph.service import build_graph

    rev = revision(session, id, revision_id, lock=True)
    mutable(rev)
    docs = session.scalars(select(Document).where(Document.revision_id == rev.id)).all()
    if not docs:
        from fastapi import HTTPException

        raise HTTPException(409, "Add a document before preparing knowledge")
    queued = []
    for doc in docs:
        doc.prepare_requested = True
        if not doc.extracted_text:
            stage = "extracted"
        elif not session.scalars(select(service.Chunk).where(service.Chunk.document_id == doc.id)).first():
            stage = "chunked"
        else:
            stage = "embedded"
        job = service.enqueue_stage(session, rev, doc, stage)
        if job.state == "failed":
            job.state = "queued"
            job.error = None
        queued.append(job.id)
    if all(
        c.embedding is not None
        for c in session.scalars(select(service.Chunk).where(service.Chunk.revision_id == rev.id))
    ) and all(d.extracted_text for d in docs):
        queue_graph(session, rev)
    return {"state": "queued", "jobs": queued, "label": "Preparing documents and fixture-backed facts"}


def queue_graph(session, rev):
    from app.features.processing.models import Job
    from app.features.evaluations.service import snapshot, fingerprint

    inputs = snapshot(session, rev)
    key = fingerprint({k: inputs[k] for k in ("ontology_id", "mapping_id", "chunks")})
    existing = session.scalars(
        select(Job).where(Job.revision_id == rev.id, Job.stage == "graph_built", Job.input_hash == key)
    ).first()
    if not existing:
        job = Job(product_id=rev.product_id, revision_id=rev.id, stage="graph_built", input_hash=key)
        session.add(job)
    elif existing.state == "failed" or (existing.state == "ready" and not rev.graph_build_id):
        existing.state = "queued"
        existing.error = None
