from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from app.features.products.models import uid, now


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("document_id", "stage", "input_hash"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"))
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    stage: Mapped[str] = mapped_column(String)
    input_hash: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String, default="queued")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[list] = mapped_column(JSON, default=list)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
