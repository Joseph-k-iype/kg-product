from alembic import op
from app.features.sources.models import Source
from app.features.documents.models import Document, Chunk
from app.features.processing.models import Job

revision = "002"
down_revision = "001"


def upgrade():
    for model in [Source, Document, Chunk, Job]:
        if model in (Document, Source):
            from sqlalchemy import MetaData

            table = model.__table__.to_metadata(MetaData())
            # Referenced tables need to be present in migration metadata for FK resolution.
            from app.features.products.models import Product, Revision

            for parent in [Product, Revision, Source]:
                parent.__table__.to_metadata(table.metadata)
            later_columns = (
                ("prepare_requested", "data_kind", "structured_data", "active")
                if model is Document
                else ("config",)
            )
            for name in later_columns:
                table._columns.remove(table.c[name])
            table.create(op.get_bind(), checkfirst=True)
        else:
            model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    for model in [Job, Chunk, Document, Source]:
        model.__table__.drop(op.get_bind())
