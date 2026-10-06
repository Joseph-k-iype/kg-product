from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.worker import run_once
from app.features.processing.models import Job
from app.features.products.models import now
from datetime import timedelta

client = TestClient(app)


def product():
    return client.post("/api/products", json={"name": "Complaints"}).json()


def upload(p, text=b"Complaint C-1042 submitted by Customer A-203. Refund requested."):
    return client.post(
        f"/api/products/{p['id']}/documents", files={"file": ("complaints.txt", text, "text/plain")}
    )


def test_original_storage_extraction_chunks_and_retry():
    p = product()
    response = upload(p)
    assert response.status_code == 201
    d = response.json()
    assert (
        client.get(f"/api/documents/{d['id']}/original").content
        == b"Complaint C-1042 submitted by Customer A-203. Refund requested."
    )
    assert run_once("test-worker")
    assert run_once("test-worker")
    detail = client.get(f"/api/documents/{d['id']}").json()
    assert detail["chunks"][0]["text"] == "Complaint C-1042 submitted by Customer A-203. Refund requested."
    assert detail["chunks"][0]["start"] == 0
    assert detail["chunks"][0]["end"] == 63
    assert detail["processing_version"] == "extract-v1/chunk-v1"
    assert client.post(f"/api/jobs/{detail['jobs'][0]['id']}/retry").status_code == 409


def test_empty_and_failed_extraction_have_actionable_state():
    p = product()
    assert upload(p, b"").status_code == 422
    d = client.post(
        f"/api/products/{p['id']}/documents", files={"file": ("broken.pdf", b"not a pdf", "application/pdf")}
    ).json()
    run_once("test-worker")
    detail = client.get(f"/api/documents/{d['id']}").json()
    assert detail["jobs"][0]["state"] == "failed"
    assert detail["jobs"][0]["stage"] == "extracted"
    assert detail["jobs"][0]["error"]
    assert client.get(f"/api/documents/{d['id']}/original").content == b"not a pdf"
    assert client.post(f"/api/jobs/{detail['jobs'][0]['id']}/retry").status_code == 200
    run_once("test-worker")
    retried = client.get(f"/api/documents/{d['id']}").json()
    assert retried["jobs"][0]["attempt_count"] == 2
    assert len(retried["chunks"]) == 0


def test_abandoned_lease_recovers_and_preserves_attempt_history():
    p = product()
    d = upload(p).json()
    with SessionLocal() as s:
        j = s.query(Job).first()
        j.state = "running"
        j.lease_until = now() - timedelta(minutes=1)
        j.attempt_count = 1
        s.commit()
    run_once("replacement-worker")
    detail = client.get(f"/api/documents/{d['id']}").json()
    assert detail["jobs"][0]["state"] == "ready"
    assert detail["jobs"][0]["attempt_count"] == 2


def test_source_registration_is_not_a_live_connection():
    p = product()
    response = client.post(
        "/api/sources",
        json={
            "name": "Support records",
            "type": "external",
            "owner": "Maya",
            "location": "https://example.com/support",
            "freshness_days": 7,
            "product_ids": [p["id"]],
        },
    )
    assert response.status_code == 201
    assert response.json()["connection_state"] == "registered"
    assert (
        client.post(f"/api/sources/{response.json()['id']}/sync-fixture").json()["label"]
        == "Fixture synchronization"
    )


def test_worker_executes_in_its_own_process_without_api_model_imports():
    import subprocess, sys, os

    p = product()
    d = upload(p).json()
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            'from app.worker import run_once; run_once("isolated-worker"); run_once("isolated-worker")',
        ],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    detail = client.get(f"/api/documents/{d['id']}").json()
    assert detail["jobs"][0]["state"] == "ready", detail["jobs"][0]["error"]
    assert len(detail["chunks"]) == 1
