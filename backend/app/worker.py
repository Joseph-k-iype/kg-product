import logging
import time
from datetime import timedelta
from sqlalchemy import select, or_, and_
from app.db import SessionLocal
from app.features.products.models import now, Revision
from app.features.processing.models import Job
from app.features.documents.models import Document
from app.features.sources.models import Source
from app.features.documents.service import enqueue_stage
from app.features.processing.extraction import extract, chunk

logger = logging.getLogger(__name__)


def run_once(worker_id: str) -> bool:
    with SessionLocal() as session:
        job = session.scalars(
            select(Job)
            .where(or_(Job.state == "queued", and_(Job.state == "running", Job.lease_until < now())))
            .order_by(Job.created_at)
            .with_for_update(skip_locked=True)
        ).first()
        if not job:
            return False
        job.state = "running"
        job.worker_id = worker_id
        job.lease_until = now() + timedelta(minutes=30)
        job.attempt_count += 1
        job.attempts = [
            *job.attempts,
            {
                "number": job.attempt_count,
                "worker": worker_id,
                "started_at": now().isoformat(),
                "state": "running",
            },
        ]
        job_id = job.id
        revision_id = job.revision_id
        attempt = job.attempt_count
        session.commit()
    try:
        with SessionLocal() as session:
            # Revision-before-job is the mutation lock order used by API preparation and edits.
            rev = session.scalars(select(Revision).where(Revision.id == revision_id).with_for_update()).one()
            job = session.scalars(select(Job).where(Job.id == job_id).with_for_update()).one()
            if job.attempt_count != attempt:
                return True
            doc = session.get(Document, job.document_id) if job.document_id else None
            if rev.state == "published":
                raise ValueError("Published revision is read-only.")
            if job.stage == "extracted":
                extract(session, doc)
                enqueue_stage(session, rev, doc, "chunked")
            elif job.stage == "chunked":
                chunk(session, doc)
                if doc.prepare_requested:
                    enqueue_stage(session, rev, doc, "embedded")
            elif job.stage == "embedded":
                from app.features.processing.embedding_stage import embed_document

                embed_document(session, doc, rev)
                session.flush()
                from app.features.documents.models import Chunk
                from app.features.documents.routes import queue_graph

                all_docs = session.scalars(select(Document).where(Document.revision_id == rev.id)).all()
                all_chunks = session.scalars(select(Chunk).where(Chunk.revision_id == rev.id)).all()
                if (
                    all_docs
                    and all(d.extracted_text for d in all_docs)
                    and all_chunks
                    and all(c.embedding is not None for c in all_chunks)
                ):
                    queue_graph(session, rev)
            elif job.stage == "graph_built":
                from app.features.graph.service import build_graph

                build_graph(session, rev)
                from app.features.evaluations.service import evaluate

                evaluate(session, rev)
                for document in session.scalars(select(Document).where(Document.revision_id == rev.id)):
                    document.state = "validated"
            else:
                raise ValueError("Unknown processing stage")
            if doc:
                doc.state = job.stage
            job.state = "ready"
            job.error = None
            job.lease_until = None
            job.attempts = [
                *job.attempts[:-1],
                {**job.attempts[-1], "state": "ready", "finished_at": now().isoformat()},
            ]
            session.commit()
    except Exception as e:
        logger.warning("Stage failed: %s", e)
        with SessionLocal() as session:
            job = session.get(Job, job_id)
            if job.attempt_count == attempt:
                job.state = "failed"
                job.error = str(e)[:2000]
                job.lease_until = None
                job.attempts = [
                    *job.attempts[:-1],
                    {
                        **job.attempts[-1],
                        "state": "failed",
                        "error": job.error,
                        "finished_at": now().isoformat(),
                    },
                ]
                session.commit()
    return True


if __name__ == "__main__":
    import socket

    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            if not run_once(socket.gethostname()):
                time.sleep(1)
        except Exception:
            logger.exception("Worker unavailable")
            time.sleep(3)
