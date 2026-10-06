from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from app.db import get_session
from app.features.products import service
from app.features.products.models import Product, Activity
from app.features.products.schemas import ProductCreate, ProductUpdate
router = APIRouter(prefix='/api')

@router.get('/products')
def catalog(q:str='',domain:str='',owner:str='',state:str='',sort:str='name',offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=200),session=Depends(get_session)):
    return service.catalog(session,q,domain,owner,state,sort,offset,limit)
@router.post('/products',status_code=201)
def create(input:ProductCreate,session=Depends(get_session)):
    return service.create_product(session,input)
@router.get('/products/{id}')
def get(id:str,session=Depends(get_session)):
    return service.detail(session,service.require(session,Product,id))
@router.patch('/products/{id}')
def update(id:str,input:ProductUpdate,session=Depends(get_session)):
    return service.update_draft(session,id,input)
@router.post('/products/{id}/draft')
def draft(id:str,session=Depends(get_session)):
    return service.open_draft(session,id)
@router.get('/products/{id}/activity')
def activity(id:str,session=Depends(get_session)):
    return session.scalars(select(Activity).where(Activity.product_id==id).order_by(Activity.created_at.desc())).all()
