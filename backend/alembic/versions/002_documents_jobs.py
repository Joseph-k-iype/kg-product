from alembic import op
from app.features.sources.models import Source
from app.features.documents.models import Document,Chunk
from app.features.processing.models import Job
revision='002'
down_revision='001'
def upgrade():
    for model in [Source,Document,Chunk,Job]:model.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():
    for model in [Job,Chunk,Document,Source]:model.__table__.drop(op.get_bind())
