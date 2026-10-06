import json
from hashlib import sha256

from sqlalchemy import or_, select

from app.features.documents.models import Document
from app.features.documents.service import upload_document
from app.features.processing.models import Job
from app.features.products.models import now


def save_snapshot(session, rev, source, result):
    identity = sha256(result["data"] + json.dumps(result["normalized"], sort_keys=True).encode()).hexdigest()
    old = session.scalars(
        select(Document).where(
            Document.revision_id == rev.id, Document.source_id == source.id, Document.active.is_(True)
        )
    ).all()
    for doc in old:
        if doc.structured_data.get("snapshot_identity") == identity:
            return doc.id
    normalized = {**result["normalized"], "snapshot_identity": identity, "source_snapshot": True}
    imported = upload_document(
        session,
        rev.product_id,
        source.name + "-snapshot" + result["extension"],
        result["data"],
        result["media_type"],
        rev.id,
        source.id,
        normalized,
    )
    retired = [d.id for d in old if d.structured_data.get("source_snapshot")]
    for doc in old:
        if doc.id in retired:
            doc.active, doc.state = False, "superseded"
    if retired:
        jobs = session.scalars(
            select(Job).where(
                Job.revision_id == rev.id,
                or_(Job.document_id.in_(retired), Job.document_id.is_(None)),
                Job.state != "ready",
            )
        ).all()
        for job in jobs:
            job.state, job.error = "superseded", None
            if job.attempts and job.attempts[-1]["state"] == "running":
                job.attempts = [
                    *job.attempts[:-1],
                    {**job.attempts[-1], "state": "superseded", "finished_at": now().isoformat()},
                ]
    return imported["id"]
