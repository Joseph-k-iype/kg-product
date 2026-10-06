from alembic import op
from app.features.products.models import Product, Revision, Activity

revision = "001"
down_revision = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    for model in [Product, Revision, Activity]:
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    for model in [Activity, Revision, Product]:
        model.__table__.drop(op.get_bind())
