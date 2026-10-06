from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app


def test_product_is_committed_before_success_response_starts():
    observed = []

    async def observed_app(scope, receive, send):
        async def observe(message):
            if message["type"] == "http.response.start":
                with engine.connect() as connection:
                    observed.append(
                        connection.scalar(
                            text("SELECT count(*) FROM products WHERE name = 'Committed before response'")
                        )
                    )
            await send(message)

        await app(scope, receive, observe)

    response = TestClient(observed_app).post("/api/products", json={"name": "Committed before response"})
    assert response.status_code == 201
    assert observed == [1]


def test_failed_commit_never_returns_creation_success(monkeypatch):
    def fail_commit(session):
        raise RuntimeError("Simulated database commit failure")

    monkeypatch.setattr(Session, "commit", fail_commit)
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/products", json={"name": "Must roll back"}
    )
    assert response.status_code == 500
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM products")) == 0
