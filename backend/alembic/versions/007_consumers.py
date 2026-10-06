from alembic import op
from app.features.consumers.models import Consumer
revision='007'
down_revision='006'
def upgrade():Consumer.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():Consumer.__table__.drop(op.get_bind())
