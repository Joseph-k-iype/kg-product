import math
import time
from dataclasses import asdict
from fastapi import HTTPException
from sqlalchemy import select
from app.features.products.service import revision, require
from app.features.products.models import Product
from app.features.documents.models import Chunk, Document
from app.domain.contracts import ModelRef
from app.adapters.embeddings import EmbeddingProvider, MODEL_NAME, MODEL_REVISION

provider = EmbeddingProvider()


def default_model() -> ModelRef:
    return ModelRef(MODEL_NAME, MODEL_REVISION, 384)


def store_embedding(chunk, vector: list[float], model: ModelRef):
    if (
        model.dimension != 384
        or len(vector) != 384
        or any(not math.isfinite(v) for v in vector)
        or sum(v * v for v in vector) == 0
    ):
        raise ValueError("Vector dimensions and model identity must match the 384-dimensional index.")
    chunk.embedding = vector
    chunk.model_name = model.name
    chunk.model_revision = model.revision
    chunk.model_dimension = model.dimension


def resolve_inputs(session, pid, preview, revision_id=None, release_id=None):
    if preview:
        rev = revision(session, pid, revision_id)
        chunks = session.scalars(
            select(Chunk).where(Chunk.product_id == pid, Chunk.revision_id == rev.id)
        ).all()
        return rev, [c.id for c in chunks], None
    from app.features.releases.models import Release

    product = require(session, Product, pid)
    release = require(session, Release, release_id or product.active_release_id or "")
    if release.product_id != pid:
        raise HTTPException(404, "Release not found for this product")
    rev = revision(session, pid, release.revision_id)
    return rev, release.manifest["chunk_ids"], release


def search_vector(session, ref, model: ModelRef, query: str, limit: int, chunk_ids=None):
    chunks_query = select(Chunk).where(Chunk.product_id == ref.product_id, Chunk.revision_id == ref.id)
    if chunk_ids is not None:
        chunks_query = chunks_query.where(Chunk.id.in_(chunk_ids))
    chunks = session.scalars(chunks_query).all()
    if not chunks or any(c.embedding is None for c in chunks):
        raise HTTPException(
            409,
            {
                "code": "knowledge_not_prepared",
                "message": "Prepare all documents before searching this version.",
            },
        )
    if any(
        (c.model_name, c.model_revision, c.model_dimension) != (model.name, model.revision, model.dimension)
        for c in chunks
    ):
        raise HTTPException(
            409,
            {
                "code": "model_mismatch",
                "message": "This version was prepared with a different search model. Use its configured model.",
            },
        )
    try:
        vector = provider.embed([query], model)[0]
    except Exception as e:
        raise HTTPException(503, {"code": "embedding_provider_unavailable", "message": str(e)})
    if len(vector) != model.dimension or any(not math.isfinite(v) for v in vector):
        raise HTTPException(422, "Query vector is incompatible")
    distance = Chunk.embedding.cosine_distance(vector)
    ranked = session.execute(
        chunks_query.add_columns(distance.label("distance")).order_by(distance).limit(limit)
    ).all()
    return [
        {
            "score": round(1 - float(dist), 5),
            "evidence": {
                "chunk_id": c.id,
                "document_id": c.document_id,
                "text": c.text,
                "start": c.start,
                "end": c.end,
                "processing_version": c.processing_version,
                "document_name": require(session, Document, c.document_id).name,
                "source_url": f"/api/documents/{c.document_id}/original",
            },
        }
        for c, dist in ranked
    ]


def retrieve(session, pid, input):
    start = time.perf_counter()
    rev, chunk_ids, release = resolve_inputs(session, pid, input.preview, input.revision_id, input.release_id)
    config = (
        release.manifest.get("embedding_model", asdict(default_model()))
        if release
        else rev.config.get("embedding_model", asdict(default_model()))
    )
    model = ModelRef(**(input.model or config))
    if input.mode == "vector":
        results = search_vector(session, rev, model, input.query, input.limit, chunk_ids)
    elif input.mode == "graph":
        from app.features.graph.service import graph_retrieval

        results = graph_retrieval(session, rev, input.query, input.limit, release)
    elif input.mode == "hybrid":
        results = search_vector(session, rev, model, input.query, input.limit, chunk_ids)
        from app.features.graph.service import graph_context

        for result in results:
            result["related_facts"] = graph_context(
                session, rev, result["evidence"]["chunk_id"], input.limit, release
            )
    else:
        raise HTTPException(422, "Choose a supported search mode")
    return {
        "results": results,
        "diagnostics": {
            "model": asdict(model),
            "revision_id": rev.id,
            "generation": rev.generation,
            "release_id": release.id if release else None,
            "preview": input.preview,
            "mode": input.mode,
            "elapsed_ms": round((time.perf_counter() - start) * 1000),
            "chunk_snapshot_count": len(chunk_ids),
        },
        "label": "Draft preview" if input.preview else "Published release",
    }
