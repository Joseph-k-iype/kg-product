from sqlalchemy import select
from fastapi import HTTPException
from app.features.reviews.models import Review
from app.features.products.models import Product,Revision,Activity
from app.features.products.service import require,mutable
from app.features.evaluations.service import current_pass,fingerprint,snapshot

def review_detail(session,review):
    rev=require(session,Revision,review.revision_id)
    current=review.input_hash==fingerprint(snapshot(session,rev))
    return {'id':review.id,'product_id':review.product_id,'product_name':require(session,Product,review.product_id).name,'revision_id':review.revision_id,'generation':review.generation,'state':review.state if current else 'superseded','summary':review.summary,'requester':review.requester,'reviewer_id':review.reviewer_id,'decision_reason':review.decision_reason,'changes':review.changes,'evaluation_id':review.evaluation_id,'created_at':review.created_at}

def submit_review(session,rev,summary):
    mutable(rev);run=current_pass(session,rev)
    existing=session.scalars(select(Review).where(Review.revision_id==rev.id,Review.input_hash==run.input_hash,Review.state=='submitted')).first()
    if existing:return review_detail(session,existing)
    from app.features.releases.models import Release
    product=require(session,Product,rev.product_id)
    before=session.get(Release,product.active_release_id) if product.active_release_id else None
    review=Review(product_id=rev.product_id,revision_id=rev.id,generation=rev.generation,evaluation_id=run.id,input_hash=run.input_hash,summary=summary,changes={'before':before.manifest if before else None,'after':run.inputs,'quality_evidence':run.metrics})
    session.add(review);rev.state='submitted';session.flush()
    session.add(Activity(product_id=rev.product_id,revision_id=rev.id,action='Approval requested'))
    return review_detail(session,review)

def decide_review(session,review_id,decision,reason,reviewer_id):
    review=require(session,Review,review_id);rev=session.scalars(select(Revision).where(Revision.id==review.revision_id).with_for_update()).one()
    if review.state!='submitted' or review_detail(session,review)['state']=='superseded':raise HTTPException(409,{'code':'stale_review','message':'This approval request changed. Request a new review.'})
    if reviewer_id==review.requester:raise HTTPException(422,'Choose a different demo reviewer')
    if decision=='reject' and not reason.strip():raise HTTPException(422,'Explain why changes are required')
    current_pass(session,rev)
    review.state='approved' if decision=='approve' else 'rejected';review.decision_reason=reason;review.reviewer_id=reviewer_id
    rev.state='approved' if decision=='approve' else 'draft'
    session.add(Activity(product_id=rev.product_id,revision_id=rev.id,action='Approved' if decision=='approve' else 'Changes requested',actor=reviewer_id))
    return review_detail(session,review)
