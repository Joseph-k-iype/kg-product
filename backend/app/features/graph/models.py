from sqlalchemy import String,Integer,ForeignKey,JSON,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from app.db import Base
from app.features.products.models import uid
class GraphBuild(Base):
    __tablename__='graph_builds'
    __table_args__=(UniqueConstraint('revision_id','input_hash'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    product_id:Mapped[str]=mapped_column(ForeignKey('products.id'))
    revision_id:Mapped[str]=mapped_column(ForeignKey('revisions.id'))
    generation:Mapped[int]=mapped_column(Integer)
    ontology_id:Mapped[str]=mapped_column(ForeignKey('ontologies.id'))
    mapping_id:Mapped[str]=mapped_column(ForeignKey('mappings.id'))
    input_hash:Mapped[str]=mapped_column(String)
    graph_key:Mapped[str]=mapped_column(String)
    state:Mapped[str]=mapped_column(String,default='preparing')
    instances:Mapped[list]=mapped_column(JSON,default=list)
    relationships:Mapped[list]=mapped_column(JSON,default=list)
    extraction_version:Mapped[str]=mapped_column(String,default='fixture-rules-v1')
class FactFlag(Base):
    __tablename__='fact_flags'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    product_id:Mapped[str]=mapped_column(ForeignKey('products.id'))
    revision_id:Mapped[str]=mapped_column(ForeignKey('revisions.id'))
    build_id:Mapped[str]=mapped_column(ForeignKey('graph_builds.id'))
    entity_id:Mapped[str]=mapped_column(String)
    reason:Mapped[str]=mapped_column(String)
    author:Mapped[str]=mapped_column(String,default='Demo author')
    state:Mapped[str]=mapped_column(String,default='open')
