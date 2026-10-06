from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from app.config import settings

url = make_url(settings.database_url).set(database="postgres")
with create_engine(url, isolation_level="AUTOCOMMIT").connect() as connection:
    if not connection.scalar(
        text("SELECT 1 FROM pg_database WHERE datname='knowledge_test'")
    ):
        connection.execute(text("CREATE DATABASE knowledge_test"))
print("Dedicated knowledge_test database ready.")
