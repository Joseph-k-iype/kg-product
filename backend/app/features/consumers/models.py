from sqlalchemy import String,ForeignKey,JSON
from sqlalchemy.orm import Mapped,mapped_column
from app.db import Base
from app.features.products.models import uid
class Consumer(Base):
    __tablename__='consumers'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    name:Mapped[str]=mapped_column(String)
    type:Mapped[str]=mapped_column(String)
    product_id:Mapped[str]=mapped_column(ForeignKey('products.id'))
    release_policy:Mapped[str]=mapped_column(String)
    release_id:Mapped[str|None]=mapped_column(ForeignKey('releases.id'),nullable=True)
    usage:Mapped[dict]=mapped_column(JSON,default=lambda:{'label':'Simulated demo usage','requests_last_7_days':0})
