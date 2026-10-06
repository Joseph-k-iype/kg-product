from alembic import op
from app.features.retrieval.models import EvaluationCase
revision='004'
down_revision='003'
def upgrade():
    EvaluationCase.__table__.create(op.get_bind(),checkfirst=True)
    op.execute('CREATE INDEX IF NOT EXISTS chunks_scope_idx ON chunks (product_id,revision_id)')
    op.execute('CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops)')
def downgrade():
    EvaluationCase.__table__.drop(op.get_bind())
