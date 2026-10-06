from sqlalchemy import String, Integer, ForeignKey, DateTime, UniqueConstraint, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db import Base
from app.features.products.models import uid, now
from datetime import datetime


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"))
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    name: Mapped[str] = mapped_column(String)
    data_kind: Mapped[str] = mapped_column(String, default="document")
    structured_data: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    content_type: Mapped[str] = mapped_column(String)
    object_key: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    extracted_key: Mapped[str | None] = mapped_column(String, nullable=True)
    extracted_sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, default="uploaded")
    prepare_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_version: Mapped[str] = mapped_column(String, default="extract-v1/chunk-v1")
    uploaded_by: Mapped[str] = mapped_column(String, default="Demo author")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("document_id", "ordinal", "processing_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    ordinal: Mapped[int] = mapped_column(Integer)
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String)
    processing_version: Mapped[str] = mapped_column(String)
    embedding: Mapped[list | None] = mapped_column(Vector(384), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    model_revision: Mapped[str | None] = mapped_column(String, nullable=True)
    model_dimension: Mapped[int | None] = mapped_column(Integer, nullable=True)
