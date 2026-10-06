from sqlalchemy import select
from app.features.products.models import Product, Revision, now
from app.features.products.service import detail
from app.features.documents.models import Document, Chunk
from app.features.processing.models import Job
from app.features.evaluations.models import EvaluationRun
from app.features.evaluations.service import run_detail
from app.features.reviews.models import Review
from app.features.reviews.service import review_detail
from app.features.releases.models import Release
from app.features.releases.service import release_detail
from app.features.sources.models import Source
from app.features.consumers.models import Consumer


def overview(session):
    products = session.scalars(select(Product).order_by(Product.name)).all()
    rows = []
    attention = []
    reviews = [review_detail(session, r) for r in session.scalars(select(Review))]
    for p in products:
        info = detail(session, p)
        rev = session.scalars(
            select(Revision).where(Revision.product_id == p.id).order_by(Revision.number.desc())
        ).first()
        docs = session.scalars(select(Document).where(Document.revision_id == rev.id)).all()
        chunks = session.scalars(select(Chunk).where(Chunk.revision_id == rev.id)).all()
        ready = sum(
            bool(d.extracted_text)
            and all(c.embedding is not None for c in chunks if c.document_id == d.id)
            and any(c.document_id == d.id for c in chunks)
            for d in docs
        )
        evaluation = session.scalars(
            select(EvaluationRun)
            .where(EvaluationRun.revision_id == rev.id)
            .order_by(EvaluationRun.created_at.desc())
        ).first()
        quality = run_detail(session, evaluation, rev)["state"] if evaluation else "not_checked"
        jobs = session.scalars(select(Job).where(Job.revision_id == rev.id, Job.state == "failed")).all()
        consumer_count = len(session.scalars(select(Consumer).where(Consumer.product_id == p.id)).all())
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
    for source in session.scalars(select(Source)):
        if source.last_synced_at is None or (now() - source.last_synced_at).days > source.freshness_days:
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
