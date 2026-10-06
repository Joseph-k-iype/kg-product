from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from app.db import get_session
from app.features.products.service import revision
from app.features.graph import service
from app.features.graph.models import FactFlag

router = APIRouter(prefix="/api/products/{id}")


@router.post("/graph/build")
def build(id: str, revision_id: str | None = None, session=Depends(get_session, scope="function")):
    return service.build_graph(session, revision(session, id, revision_id, lock=True))


@router.get("/entities")
def entities(
    id: str,
    q: str = "",
    entity_type: str | None = None,
    revision_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    session=Depends(get_session, scope="function"),
):
    rev = revision(session, id, revision_id)
    build = service.resolve_build(session, rev)
    return {
        "items": service.adapter.search(build, q, entity_type, limit),
        "build": service.build_detail(build),
    }


@router.get("/entities/{entity_id}/neighbors")
def neighbors(
    id: str,
    entity_id: str,
    revision_id: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    session=Depends(get_session, scope="function"),
):
    build = service.resolve_build(session, revision(session, id, revision_id))
    return service.adapter.neighbors(build, entity_id, limit)


class FlagInput(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


@router.post("/entities/{entity_id}/flags", status_code=201)
def flag(
    id: str, entity_id: str, input: FlagInput, revision_id: str | None = None, session=Depends(get_session, scope="function")
):
    rev = revision(session, id, revision_id)
    build = service.resolve_build(session, rev)
    if not any(n["id"] == entity_id for n in build.instances):
        raise HTTPException(404, "Fact not found")
    item = FactFlag(
        product_id=id, revision_id=rev.id, build_id=build.id, entity_id=entity_id, reason=input.reason
    )
    session.add(item)
    session.flush()
    return {"id": item.id, "state": item.state}
