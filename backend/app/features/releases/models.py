from sqlalchemy import String,Integer,ForeignKey,JSON,DateTime,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from datetime import datetime
from app.db import Base
from app.features.products.models import uid,now
class Release(Base):
    __tablename__='releases'
    __table_args__=(UniqueConstraint('product_id','number'),UniqueConstraint('revision_id'))
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    product_id:Mapped[str]=mapped_column(ForeignKey('products.id'))
    revision_id:Mapped[str]=mapped_column(ForeignKey('revisions.id'))
    number:Mapped[int]=mapped_column(Integer)
    manifest:Mapped[dict]=mapped_column(JSON)
    object_key:Mapped[str]=mapped_column(String)
    sha256:Mapped[str]=mapped_column(String)
    published_by:Mapped[str]=mapped_column(String,default='demo-publisher')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
