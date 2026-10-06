from alembic import op
from app.features.evaluations.models import EvaluationRun
from app.features.reviews.models import Review
from app.features.releases.models import Release

revision = "006"
down_revision = "005"


def upgrade():
    for model in [EvaluationRun, Review, Release]:
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    for model in [Release, Review, EvaluationRun]:
        model.__table__.drop(op.get_bind())
