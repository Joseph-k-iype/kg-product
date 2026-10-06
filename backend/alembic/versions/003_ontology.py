from alembic import op
from app.features.ontology.models import OntologyVersion, MappingVersion

revision = "003"
down_revision = "002"


def upgrade():
    for model in [OntologyVersion, MappingVersion]:
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    for model in [MappingVersion, OntologyVersion]:
        model.__table__.drop(op.get_bind())
