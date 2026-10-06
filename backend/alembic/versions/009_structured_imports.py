from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"


def upgrade():
    op.add_column("documents", sa.Column("data_kind", sa.String(), nullable=False, server_default="document"))
    op.add_column("documents", sa.Column("structured_data", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("sources", sa.Column("config", sa.JSON(), nullable=False, server_default="{}"))


def downgrade():
    op.drop_column("sources", "config")
    op.drop_column("documents", "structured_data")
    op.drop_column("documents", "data_kind")
