from sqlalchemy import select
from app.features.documents.models import Chunk
from app.features.retrieval.service import default_model, store_embedding, provider
from app.domain.contracts import ModelRef
from dataclasses import asdict


def embed_document(session, doc, rev):
    model = ModelRef(**rev.config.get("embedding_model", asdict(default_model())))
    chunks = session.scalars(select(Chunk).where(Chunk.document_id == doc.id)).all()
    if not chunks:
        raise ValueError("Generate document excerpts first.")
    missing = [
        c
        for c in chunks
        if c.embedding is None or (c.model_name, c.model_revision) != (model.name, model.revision)
    ]
    if missing:
        vectors = provider.embed([c.text for c in missing], model)
        if len(vectors) != len(missing):
            raise ValueError("Search provider returned an incomplete response")
        for chunk, vector in zip(missing, vectors, strict=True):
            store_embedding(chunk, vector, model)
