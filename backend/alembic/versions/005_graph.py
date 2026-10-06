from alembic import op
from app.features.graph.models import GraphBuild,FactFlag
revision='005'
down_revision='004'
def upgrade():
    for model in [GraphBuild,FactFlag]:model.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():
    for model in [FactFlag,GraphBuild]:model.__table__.drop(op.get_bind())
