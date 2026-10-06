import os
os.environ['DATABASE_URL'] = 'postgresql+psycopg://knowledge:knowledge-local@localhost:55432/knowledge_test'
import pytest
from sqlalchemy import text
from app.db import engine

@pytest.fixture(autouse=True)
def isolated_database():
    assert engine.url.database == 'knowledge_test'
    with engine.begin() as connection:
        tables = connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename != 'alembic_version'")).scalars().all()
        if tables:
            connection.execute(text('TRUNCATE ' + ','.join('"'+t+'"' for t in tables) + ' CASCADE'))
    yield
