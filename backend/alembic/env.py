from alembic import context
from app.db import Base, engine
from app.features.products import models
from app.features.documents import models as documents
from app.features.sources import models as sources
from app.features.processing import models as processing
from app.features.ontology import models as ontology
from app.features.retrieval import models as retrieval
from app.features.graph import models as graph
from app.features.evaluations import models as evaluations
from app.features.reviews import models as reviews
from app.features.releases import models as releases
from app.features.consumers import models as consumers
with engine.connect() as connection:
    context.configure(connection=connection,target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
