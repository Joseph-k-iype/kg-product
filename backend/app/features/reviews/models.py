from sqlalchemy import String,Integer,ForeignKey,JSON,DateTime
from sqlalchemy.orm import Mapped,mapped_column
from datetime import datetime
from app.db import Base
from app.features.products.models import uid,now
class Review(Base):
    __tablename__='reviews'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    product_id:Mapped[str]=mapped_column(ForeignKey('products.id'))
    revision_id:Mapped[str]=mapped_column(ForeignKey('revisions.id'))
    generation:Mapped[int]=mapped_column(Integer)
    evaluation_id:Mapped[str]=mapped_column(ForeignKey('evaluations.id'))
    input_hash:Mapped[str]=mapped_column(String)
    summary:Mapped[str]=mapped_column(String)
    requester:Mapped[str]=mapped_column(String,default='demo-author')
    reviewer_id:Mapped[str|None]=mapped_column(String,nullable=True)
    decision_reason:Mapped[str|None]=mapped_column(String,nullable=True)
    state:Mapped[str]=mapped_column(String,default='submitted')
    changes:Mapped[dict]=mapped_column(JSON)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
