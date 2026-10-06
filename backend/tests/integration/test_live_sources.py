import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app

client = TestClient(app)


def product():
    return client.post("/api/products", json={"name": "Live records"}).json()["id"]


def test_postgres_source_reads_real_table_and_preserves_safe_credential_reference(monkeypatch):
    pid = product()
    monkeypatch.setenv(
        "SOURCE_TEST_DATABASE_URL", "postgresql://knowledge:knowledge-local@localhost:55432/knowledge_test"
    )
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS source_fixture (id integer, name text)"))
        connection.execute(text("INSERT INTO source_fixture VALUES (1,'Ana'),(2,'Ben')"))
    response = client.post(
        "/api/sources",
        json={
            "name": "Customer database",
            "type": "postgres",
            "product_ids": [pid],
            "config": {
                "credential_env": "SOURCE_TEST_DATABASE_URL",
                "schema": "public",
                "table": "source_fixture",
                "limit": 100,
            },
        },
    )
    assert response.status_code == 201, response.text
    source = response.json()
    assert "knowledge-local" not in json.dumps(source)
    checked = client.post(f"/api/sources/{source['id']}/test")
    assert checked.status_code == 200, checked.text
    assert checked.json()["record_count"] == 2
    synced = client.post(f"/api/sources/{source['id']}/sync")
    assert synced.status_code == 200, synced.text
    documents = client.get(f"/api/products/{pid}/documents").json()
    assert documents[0]["source_id"] == source["id"]
    assert documents[0]["record_count"] == 2
    assert client.get("/api/sources").json()[0]["connection_state"] == "connected"
    # A repeated snapshot of identical data reuses its source-scoped original.
    assert client.post(f"/api/sources/{source['id']}/sync").json()["documents"] == synced.json()["documents"]
    assert len(client.get(f"/api/products/{pid}/documents").json()) == 1


def test_http_api_reads_json_only_from_explicitly_allowed_origin(monkeypatch):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"data": [{"id": 1, "name": "Ana"}, {"id": 2, "name": "Ben"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        pid = product()
        source = client.post(
            "/api/sources",
            json={
                "name": "Customer API",
                "type": "api",
                "location": origin + "/records",
                "product_ids": [pid],
                "config": {"records_path": "data", "limit": 100},
            },
        )
        assert source.status_code == 201, source.text
        source_id = source.json()["id"]
        assert client.post(f"/api/sources/{source_id}/test").status_code == 422
        monkeypatch.setenv("SOURCE_API_ALLOWED_ORIGINS", origin)
        checked = client.post(f"/api/sources/{source_id}/test")
        assert checked.status_code == 200, checked.text
        assert checked.json()["sample_rows"][0]["name"] == "Ana"
        imported = client.post(f"/api/sources/{source_id}/sync")
        assert imported.status_code == 200, imported.text
        document_id = imported.json()["documents"][0]
        original = client.get(f"/api/documents/{document_id}/original")
        assert json.loads(original.content)["data"][1]["name"] == "Ben"
    finally:
        server.shutdown()
        server.server_close()


def test_sources_reject_inline_secrets_and_unconfigured_environment_references():
    for config in [{"credential_env": "DATABASE_URL"}, {"password": "private"}]:
        response = client.post(
            "/api/sources", json={"name": "Unsafe config", "type": "postgres", "config": config}
        )
        assert response.status_code == 422
    response = client.post(
        "/api/sources",
        json={
            "name": "Unconfigured",
            "type": "postgres",
            "config": {"credential_env": "SOURCE_NOT_CONFIGURED", "table": "records"},
        },
    )
    assert response.status_code == 201
    checked = client.post(f"/api/sources/{response.json()['id']}/test")
    assert checked.status_code == 422
    assert "SOURCE_NOT_CONFIGURED" in checked.text


def test_new_source_snapshot_replaces_draft_records_and_preserves_published_release(monkeypatch):
    from app.db import SessionLocal
    from app.features.documents.models import Chunk
    from app.features.retrieval.service import default_model, store_embedding
    from app.worker import run_once
    from tests.integration.test_governance import approve

    pid = product()
    monkeypatch.setenv(
        "SOURCE_TEST_DATABASE_URL", "postgresql://knowledge:knowledge-local@localhost:55432/knowledge_test"
    )
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS source_fixture (id integer, name text)"))
        connection.execute(text("INSERT INTO source_fixture VALUES (1,'Ana'),(2,'Ben')"))
    source = client.post(
        "/api/sources",
        json={
            "name": "Customer table",
            "type": "postgres",
            "product_ids": [pid],
            "config": {"credential_env": "SOURCE_TEST_DATABASE_URL", "table": "source_fixture"},
        },
    ).json()
    first = client.post(f"/api/sources/{source['id']}/sync").json()["documents"][0]
    while run_once("source-test"):
        pass
    detail = client.get(f"/api/products/{pid}").json()
    client.patch(
        f"/api/products/{pid}",
        json={"expected_generation": detail["draft"]["generation"], "purpose": "Customer records"},
    )
    with SessionLocal() as session:
        for chunk in session.query(Chunk):
            store_embedding(chunk, [1.0] + [0.0] * 383, default_model())
        session.commit()
    client.post(f"/api/products/{pid}/graph/build")
    approve(pid)
    release = client.post(f"/api/products/{pid}/releases").json()
    client.post(f"/api/products/{pid}/draft")
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM source_fixture WHERE id=2"))
        connection.execute(text("UPDATE source_fixture SET name='Updated Ana' WHERE id=1"))
    changed = client.post(f"/api/sources/{source['id']}/sync")
    assert changed.status_code == 200, changed.text
    while run_once("source-test"):
        pass
    built = client.post(f"/api/products/{pid}/graph/build")
    assert built.status_code == 200, built.text
    assert built.json()["instance_count"] == 1
    docs = client.get(f"/api/products/{pid}/documents").json()
    assert len([d for d in docs if d["active"]]) == 1
    assert b"Ben" in client.get(f"/api/documents/{first}/original").content
    published = client.post(
        f"/api/products/{pid}/retrieval", json={"query": "Ben", "mode": "graph", "release_id": release["id"]}
    ).json()
    assert published["results"][0]["entity"]["label"] == "Ben"
