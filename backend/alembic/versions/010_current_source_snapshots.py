from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"


def upgrade():
    op.add_column("documents", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    op.drop_column("documents", "active")
