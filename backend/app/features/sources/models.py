from datetime import datetime
from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from app.features.products.models import uid, now


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, default="local")
    owner: Mapped[str] = mapped_column(String)
    location: Mapped[str] = mapped_column(String, default="")
    freshness_days: Mapped[int] = mapped_column(Integer, default=30)
    product_ids: Mapped[list] = mapped_column(JSON, default=list)
    connection_state: Mapped[str] = mapped_column(String, default="registered")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
