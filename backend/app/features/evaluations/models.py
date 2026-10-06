from sqlalchemy import String, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db import Base
from app.features.products.models import uid, now


class EvaluationRun(Base):
    __tablename__ = "evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"))
    generation: Mapped[int] = mapped_column(Integer)
    input_hash: Mapped[str] = mapped_column(String)
    inputs: Mapped[dict] = mapped_column(JSON)
    metrics: Mapped[list] = mapped_column(JSON)
    findings: Mapped[list] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
