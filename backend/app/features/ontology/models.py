from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from app.features.products.models import uid, now


class OntologyVersion(Base):
    __tablename__ = "ontologies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"))
    version: Mapped[int] = mapped_column(Integer)
    object_key: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String(64))
    unsupported: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MappingVersion(Base):
    __tablename__ = "mappings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"))
    ontology_id: Mapped[str] = mapped_column(ForeignKey("ontologies.id"))
    version: Mapped[int] = mapped_column(Integer)
    definition: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
