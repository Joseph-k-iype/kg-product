from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy import select
from app.db import get_session
from app.features.consumers.models import Consumer
from app.features.consumers import service

router = APIRouter(prefix="/api/consumers")


class ConsumerInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: Literal["agent", "copilot", "api", "dashboard"]
    product_id: str
    release_policy: Literal["active", "pinned"] = "active"
    release_id: str | None = None


@router.get("")
def list_consumers(product_id: str | None = None, session=Depends(get_session)):
    query = select(Consumer).order_by(Consumer.name)
    if product_id:
        query = query.where(Consumer.product_id == product_id)
    return [service.consumer_detail(session, c) for c in session.scalars(query)]


@router.post("", status_code=201)
def create(input: ConsumerInput, session=Depends(get_session)):
    return service.save_consumer(session, input)


@router.patch("/{id}")
def update(id: str, input: ConsumerInput, session=Depends(get_session)):
    return service.save_consumer(session, input, id)


@router.get("/{id}/resolve")
def resolve(id: str, session=Depends(get_session)):
    return service.resolve_consumer(session, id)
