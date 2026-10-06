"""Explicit reset of this local application's metadata and build namespace."""

import argparse, re
from sqlalchemy import text
from redis import Redis
from app.db import engine
from app.config import settings

parser = argparse.ArgumentParser()
parser.add_argument("--confirm-reset", action="store_true")
args = parser.parse_args()
if not args.confirm_reset:
    raise SystemExit(
        "Reset removes all product metadata. Pass --confirm-reset after backing up your work."
    )
if engine.url.database != "knowledge":
    raise SystemExit("Reset is restricted to the local knowledge database.")
with engine.begin() as connection:
    tables = (
        connection.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename != 'alembic_version'"
            )
        )
        .scalars()
        .all()
    )
    if tables:
        connection.execute(
            text("TRUNCATE " + ",".join('"' + t + '"' for t in tables) + " CASCADE")
        )
redis = Redis.from_url(settings.graph_url, decode_responses=True)
for key in redis.scan_iter("kp_knowledge_*"):
    if re.fullmatch(r"kp_knowledge_[0-9a-f]{32}_[0-9a-f]{32}_[0-9a-f]{32}", key):
        redis.execute_command("GRAPH.DELETE", key)
print(
    "Local metadata and instance builds reset. Content-addressed originals remain in MinIO for recovery; seed with make seed."
)
