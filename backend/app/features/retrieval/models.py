from sqlalchemy import String,ForeignKey,JSON
from sqlalchemy.orm import Mapped,mapped_column
from app.db import Base
from app.features.products.models import uid
class EvaluationCase(Base):
    __tablename__='evaluation_cases'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    product_id:Mapped[str]=mapped_column(ForeignKey('products.id'))
    query:Mapped[str]=mapped_column(String)
    expected_document_ids:Mapped[list]=mapped_column(JSON,default=list)
