from collections import defaultdict
from datetime import timedelta

from sqlalchemy import or_, select

from app.features.consumers.models import Consumer
from app.features.documents.models import Chunk, Document
from app.features.evaluations.models import EvaluationRun
from app.features.evaluations.service import fingerprint, run_detail, snapshot
from app.features.ontology.models import MappingVersion, OntologyVersion
from app.features.processing.models import Job
from app.features.products.models import Product, Revision, now
from app.features.products.service import detail
from app.features.releases.models import Release
from app.features.releases.service import release_detail
from app.features.reviews.models import Review
from app.features.reviews.service import review_detail
from app.features.sources.models import Source


def overview(session):
    products = session.scalars(select(Product).order_by(Product.name)).all()
    rows = []
    attention = []
    # Load catalog inputs once. Retain model references so the session identity
    # map can resolve snapshot FK reads without one query per record.
    def grouped(records, key):
        groups = defaultdict(list)
        for record in records:
            groups[getattr(record, key)].append(record)
        return groups

    revisions = grouped(session.scalars(select(Revision).order_by(Revision.number.desc())).all(), "product_id")
    documents = grouped(session.scalars(select(Document).where(Document.active.is_(True)).order_by(Document.id)).all(), "revision_id")
    excerpts = grouped(session.scalars(select(Chunk).join(Document).where(Document.active.is_(True)).order_by(Chunk.id)).all(), "revision_id")
    evaluations = grouped(session.scalars(select(EvaluationRun).order_by(EvaluationRun.created_at.desc())).all(), "revision_id")
    failures = grouped(session.scalars(select(Job).outerjoin(Document).where(Job.state == "failed", or_(Job.document_id.is_(None), Document.active.is_(True)))).all(), "revision_id")
    consumers = grouped(session.scalars(select(Consumer)).all(), "product_id")
    sources = session.scalars(select(Source)).all()
    _versions = [*session.scalars(select(OntologyVersion)), *session.scalars(select(MappingVersion))]
    hashes = {}

    def current_hash(rev):
        if rev.id not in hashes:
            hashes[rev.id] = fingerprint(snapshot(session, rev, documents=documents[rev.id], chunks=excerpts[rev.id]))
        return hashes[rev.id]

    reviews = [review_detail(session, r, current_input_hash=current_hash(session.get(Revision, r.revision_id))) for r in session.scalars(select(Review))]
    for p in products:
        info = detail(session, p, revisions=revisions[p.id])
        rev = revisions[p.id][0]
        docs = [d for d in documents[rev.id] if d.data_kind != "definitions"]
        chunks = excerpts[rev.id]
        ready = sum(
            bool(d.extracted_text)
            and all(c.embedding is not None for c in chunks if c.document_id == d.id)
            and any(c.document_id == d.id for c in chunks)
            for d in docs
        )
        evaluation = evaluations[rev.id][0] if evaluations[rev.id] else None
        quality = run_detail(session, evaluation, rev, current_input_hash=current_hash(rev))["state"] if evaluation else "not_checked"
        jobs = failures[rev.id]
        consumer_count = len(consumers[p.id])
        publication = "published" if not info["draft"] else info["draft"]["state"]
        row = {
            **info,
            "documents_total": len(docs),
            "documents_ready": ready,
            "quality": quality,
            "processing": "failed"
            if jobs
            else "ready"
            if docs and ready == len(docs)
            else "needs_preparation",
            "publication": publication,
            "consumer_count": consumer_count,
            "lifecycle": "active" if p.active_release_id else "draft",
        }
        rows.append(row)
        if jobs:
            for job in jobs:
                attention.append(
                    {
                        "id": job.id,
                        "product_id": p.id,
                        "product_name": p.name,
                        "owner": p.owner,
                        "severity": "high",
                        "issue": "A document could not be prepared",
                        "action": "Retry preparation",
                        "url": f"/products/{p.id}/processing",
                        "detail": job.error,
                    }
                )
        elif not docs:
            attention.append(
                {
                    "id": "documents-" + p.id,
                    "product_id": p.id,
                    "product_name": p.name,
                    "owner": p.owner,
                    "severity": "medium",
                    "issue": "Add your first document",
                    "action": "Add documents",
                    "url": f"/products/{p.id}/sources",
                }
            )
        elif ready < len(docs):
            attention.append(
                {
                    "id": "prepare-" + p.id,
                    "product_id": p.id,
                    "product_name": p.name,
                    "owner": p.owner,
                    "severity": "medium",
                    "issue": "Documents need preparation",
                    "action": "Prepare knowledge",
                    "url": f"/products/{p.id}/processing",
                }
            )
        elif quality in ("failed", "stale", "not_checked", "insufficient_data"):
            attention.append(
                {
                    "id": "checks-" + p.id,
                    "product_id": p.id,
                    "product_name": p.name,
                    "owner": p.owner,
                    "severity": "medium",
                    "issue": "Quality checks need attention",
                    "action": "Run checks",
                    "url": f"/products/{p.id}/health",
                }
            )
        elif info["draft"] and publication == "draft":
            attention.append(
                {
                    "id": "review-" + p.id,
                    "product_id": p.id,
                    "product_name": p.name,
                    "owner": p.owner,
                    "severity": "low",
                    "issue": "Ready to request approval",
                    "action": "Request approval",
                    "url": f"/products/{p.id}/reviews",
                }
            )
    overdue = []
    for source in sources:
        if source.last_synced_at is None or now() > source.last_synced_at + timedelta(days=source.freshness_days):
            overdue.append(source)
            attention.append(
                {
                    "id": source.id,
                    "product_id": source.product_ids[0] if source.product_ids else None,
                    "product_name": source.name,
                    "owner": source.owner,
                    "severity": "medium",
                    "issue": "Source needs an update",
                    "action": "View source",
                    "url": "/sources",
                    "detail": "Registered source has no recent synchronization",
                }
            )
    releases = session.scalars(select(Release).order_by(Release.created_at.desc()).limit(8)).all()
    return {
        "summary": {
            "active_products": sum(bool(p.active_release_id) for p in products),
            "pending_reviews": sum(r["state"] == "submitted" for r in reviews),
            "blocked_releases": sum(
                r["quality"] in ("failed", "insufficient_data") and r["draft"] is not None for r in rows
            ),
            "overdue_sources": len(overdue),
        },
        "products": rows,
        "attention": attention,
        "publications": [
            {**release_detail(r), "product_name": session.get(Product, r.product_id).name} for r in releases
        ],
    }
