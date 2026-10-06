import json

from fastapi import HTTPException
from sqlalchemy import select

from app.features.evaluations.service import current_pass, fingerprint, snapshot
from app.features.products.models import Activity, Product, Revision
from app.features.products.service import mutable, require
from app.features.reviews.models import Review


def review_detail(session, review, *, current_input_hash=None):
    rev = require(session, Revision, review.revision_id)
    current = review.input_hash == (current_input_hash or fingerprint(snapshot(session, rev)))
    return {
        "id": review.id,
        "product_id": review.product_id,
        "product_name": require(session, Product, review.product_id).name,
        "revision_id": review.revision_id,
        "generation": review.generation,
        "state": review.state if current else "superseded",
        "summary": review.summary,
        "requester": review.requester,
        "reviewer_id": review.reviewer_id,
        "decision_reason": review.decision_reason,
        "changes": review.changes,
        "evaluation_id": review.evaluation_id,
        "created_at": review.created_at,
    }


def definition_diff(before, after):
    def indexed(inputs):
        result = {}
        for category in ["classes", "properties"]:
            for entry in inputs.get("definitions", {}).get(category, []):
                result[entry["iri"]] = {
                    **entry,
                    "kind": category,
                    "label": entry.get("label") or entry["iri"].rsplit("/", 1)[-1],
                }
        shapes = {}
        for entry in inputs.get("definitions", {}).get("shapes", []):
            shapes.setdefault(entry["iri"], []).append(entry)
        for identifier, constraints in shapes.items():
            result[identifier] = {
                "iri": identifier,
                "kind": "shapes",
                "label": identifier.rsplit("/", 1)[-1],
                "constraints": sorted(constraints, key=lambda entry: json.dumps(entry, sort_keys=True)),
            }
        return result

    old = indexed(before or {})
    new = indexed(after)
    return {
        "added": [new[k] for k in sorted(new.keys() - old.keys())],
        "removed": [old[k] for k in sorted(old.keys() - new.keys())],
        "changed": [
            {"before": old[k], "after": new[k]} for k in sorted(new.keys() & old.keys()) if new[k] != old[k]
        ],
    }


def submit_review(session, rev, summary):
    mutable(rev)
    run = current_pass(session, rev)
    existing = session.scalars(
        select(Review).where(
            Review.revision_id == rev.id, Review.input_hash == run.input_hash, Review.state == "submitted"
        )
    ).first()
    if existing:
        return review_detail(session, existing)
    from app.features.releases.models import Release

    product = require(session, Product, rev.product_id)
    before = session.get(Release, product.active_release_id) if product.active_release_id else None
    review = Review(
        product_id=rev.product_id,
        revision_id=rev.id,
        generation=rev.generation,
        evaluation_id=run.id,
        input_hash=run.input_hash,
        summary=summary,
        changes={
            "before": before.manifest if before else None,
            "after": run.inputs,
            "quality_evidence": run.metrics,
            "ontology_diff": definition_diff(before.manifest if before else None, run.inputs),
            "mapping_changes": {
                "before": before.manifest.get("mapping_definition") if before else None,
                "after": run.inputs.get("mapping_definition"),
            },
            "document_changes": {
                "before": [d.get("name", "Document") for d in before.manifest["documents"]] if before else [],
                "after": [d.get("name", "Document") for d in run.inputs["documents"]],
            },
        },
    )
    session.add(review)
    rev.state = "submitted"
    session.flush()
    session.add(Activity(product_id=rev.product_id, revision_id=rev.id, action="Approval requested"))
    return review_detail(session, review)


def decide_review(session, review_id, decision, reason, reviewer_id):
    review = require(session, Review, review_id)
    rev = session.scalars(select(Revision).where(Revision.id == review.revision_id).with_for_update()).one()
    if review.state != "submitted" or review_detail(session, review)["state"] == "superseded":
        raise HTTPException(
            409, {"code": "stale_review", "message": "This approval request changed. Request a new review."}
        )
    if reviewer_id == review.requester:
        raise HTTPException(422, "Choose a different demo reviewer")
    if decision == "reject" and not reason.strip():
        raise HTTPException(422, "Explain why changes are required")
    current_pass(session, rev)
    review.state = "approved" if decision == "approve" else "rejected"
    review.decision_reason = reason
    review.reviewer_id = reviewer_id
    rev.state = "approved" if decision == "approve" else "draft"
    session.add(
        Activity(
            product_id=rev.product_id,
            revision_id=rev.id,
            action="Approved" if decision == "approve" else "Changes requested",
            actor=reviewer_id,
        )
    )
    return review_detail(session, review)
