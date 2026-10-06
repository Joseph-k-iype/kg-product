from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.worker import run_once
from app.db import SessionLocal
from app.features.documents.models import Chunk
from app.features.products.models import Revision
from sqlalchemy import select
import pytest

client = TestClient(app)


@pytest.mark.model
def test_real_model_end_to_end_publication_and_retrieval():
    p = client.post(
        "/api/products",
        json={
            "name": "Journey support",
            "purpose": "Help customers find verified refund guidance",
            "owner": "Maya Chen",
            "domain": "Support",
        },
    ).json()
    pid = p["id"]
    assert (
        client.post(
            f"/api/products/{pid}/ontology/starter", json={"template": "customer-support"}
        ).status_code
        == 200
    )
    d = client.post(
        f"/api/products/{pid}/documents",
        files={
            "file": (
                "refunds.txt",
                b"Complaint C-1042 submitted by Customer A-203. Customers can request refunds within 30 days of purchase.",
                "text/plain",
            )
        },
    ).json()
    response = client.post(f"/api/products/{pid}/processing/run")
    assert response.status_code == 200
    for _ in range(10):
        if not run_once("journey-worker"):
            break
    detail = client.get(f"/api/documents/{d['id']}").json()
    assert all(j["state"] == "ready" for j in detail["jobs"])
    assert detail["chunks"][0]["embedded"]
    checks = client.post(f"/api/products/{pid}/evaluations").json()
    assert checks["state"] == "passed", checks
    r = client.post(
        f"/api/products/{pid}/reviews", json={"summary": "Customer refund knowledge ready"}
    ).json()
    assert (
        client.post(
            f"/api/reviews/{r['id']}/decision",
            json={"decision": "approve", "reason": "Verified citations", "reviewer_id": "demo-reviewer"},
        ).status_code
        == 200
    )
    release = client.post(f"/api/products/{pid}/releases").json()
    assert release["manifest"]["embedding_model"]["dimension"] == 384
    hits = client.post(
        f"/api/products/{pid}/retrieval",
        json={"query": "How long do I have to ask for my money back?", "mode": "vector"},
    ).json()
    assert hits["label"] == "Published release"
    assert hits["results"][0]["evidence"]["document_id"] == d["id"]
    assert "30 days" in hits["results"][0]["evidence"]["text"]
    assert hits["results"][0]["score"] > 0.2
    hybrid = client.post(
        f"/api/products/{pid}/retrieval", json={"query": "customer refund", "mode": "hybrid"}
    ).json()
    assert hybrid["results"][0]["related_facts"][0]["relationships"]
    assert (
        client.post(
            "/api/consumers",
            json={
                "name": "Copilot",
                "type": "copilot",
                "product_id": pid,
                "release_policy": "pinned",
                "release_id": release["id"],
            },
        ).status_code
        == 201
    )
