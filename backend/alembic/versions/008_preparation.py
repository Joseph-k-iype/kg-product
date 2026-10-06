from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"


def upgrade():
    op.add_column(
        "documents", sa.Column("prepare_requested", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.execute(
        "CREATE UNIQUE INDEX jobs_revision_stage_idx ON jobs (revision_id,stage,input_hash) WHERE document_id IS NULL"
    )


def downgrade():
    op.drop_index("jobs_revision_stage_idx", table_name="jobs")
    op.drop_column("documents", "prepare_requested")
