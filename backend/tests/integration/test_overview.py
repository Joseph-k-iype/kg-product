from fastapi.testclient import TestClient
from sqlalchemy import event

from app.db import engine
from app.main import app

client = TestClient(app)


def test_overview_does_not_query_each_product_separately():
    for number in range(25):
        assert client.post("/api/products", json={"name": f"Catalog {number}"}).status_code == 201
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        response = client.get("/api/overview")
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert response.status_code == 200
    assert len(response.json()["products"]) == 25
    assert len(statements) <= 25, f"Overview issued {len(statements)} SQL statements for 25 products"


def test_overview_recomputes_current_checks_and_reviews_after_freshness_expires(monkeypatch):
    from datetime import timedelta

    from app.features.evaluations import service
    from tests.integration.test_governance import ready

    product, _ = ready()
    pid = product["id"]
    assert client.post(f"/api/products/{pid}/evaluations").json()["state"] == "passed"
    assert client.post(f"/api/products/{pid}/reviews", json={"summary": "Current evidence"}).status_code == 200
    current = client.get("/api/overview").json()
    assert current["products"][0]["quality"] == "passed"
    assert current["summary"]["pending_reviews"] == 1
    expired = service.now() + timedelta(days=31)
    monkeypatch.setattr(service, "now", lambda: expired)
    stale = client.get("/api/overview").json()
    assert stale["products"][0]["quality"] == "stale"
    assert stale["summary"]["pending_reviews"] == 0


def test_overview_excludes_failed_jobs_from_superseded_source_documents():
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.features.documents.models import Document
    from app.features.processing.models import Job

    product = client.post("/api/products", json={"name": "Current snapshot"}).json()
    document = client.post(f"/api/products/{product['id']}/documents", files={"file": ("previous.txt", b"Previous evidence", "text/plain")}).json()
    with SessionLocal() as session:
        session.get(Document, document["id"]).active = False
        job = session.scalars(select(Job).where(Job.document_id == document["id"])).first()
        job.state, job.error = "failed", "Failure in previous source snapshot"
        session.commit()
    response = client.get("/api/overview").json()
    assert response["products"][0]["processing"] == "needs_preparation"
    assert all(item.get("detail") != "Failure in previous source snapshot" for item in response["attention"])


def test_overview_source_expiry_uses_the_exact_freshness_deadline():
    from datetime import timedelta

    from app.db import SessionLocal
    from app.features.products.models import now
    from app.features.sources.models import Source

    source = client.post("/api/sources", json={"name": "Recently expired", "freshness_days": 30}).json()
    with SessionLocal() as session:
        session.get(Source, source["id"]).last_synced_at = now() - timedelta(days=30, seconds=1)
        session.commit()
    assert client.get("/api/overview").json()["summary"]["overdue_sources"] == 1
