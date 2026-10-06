from fastapi import APIRouter,Depends
from sqlalchemy import select
from pydantic import BaseModel,Field
from typing import Literal
from app.db import get_session
from app.features.products.service import revision
from app.features.reviews import service
from app.features.reviews.models import Review
router=APIRouter(prefix='/api')
class SubmitInput(BaseModel):summary:str=Field(min_length=1,max_length=3000)
class DecisionInput(BaseModel):
    decision:Literal['approve','reject']
    reason:str=''
    reviewer_id:Literal['demo-reviewer','demo-author']='demo-reviewer'
@router.get('/reviews')
def reviews(product_id:str|None=None,session=Depends(get_session)):
    query=select(Review).order_by(Review.created_at.desc())
    if product_id:query=query.where(Review.product_id==product_id)
    return [service.review_detail(session,r) for r in session.scalars(query)]
@router.post('/products/{id}/reviews')
def submit(id:str,input:SubmitInput,revision_id:str|None=None,session=Depends(get_session)):
    return service.submit_review(session,revision(session,id,revision_id,lock=True),input.summary)
@router.post('/reviews/{id}/decision')
def decide(id:str,input:DecisionInput,session=Depends(get_session)):
    return service.decide_review(session,id,input.decision,input.reason,input.reviewer_id)
