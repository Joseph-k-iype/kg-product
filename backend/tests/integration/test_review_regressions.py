from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import timedelta
from threading import Event
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db import SessionLocal
from app.worker import run_once
from app.features.products.models import Revision
from app.features.processing.models import Job
from app.features.documents.routes import queue_graph
from tests.integration.test_governance import ready, approve
from tests.integration.test_graph import prepared

client = TestClient(app)


def test_prepare_after_metadata_edit_restores_facts():
    p, d = ready()
    pid = p["id"]
    client.post(f"/api/products/{pid}/processing/run")
    while run_once("test"):
        pass
    before = client.get(f"/api/products/{pid}").json()
    client.patch(
        f"/api/products/{pid}",
        json={"expected_generation": before["draft"]["generation"], "purpose": "Updated purpose"},
    )
    client.post(f"/api/products/{pid}/processing/run")
    while run_once("test"):
        pass
    result = client.get(f"/api/products/{pid}").json()
    assert result["draft"]["graph_build_id"] is not None
    assert client.get(f"/api/products/{pid}/entities").status_code == 200


def test_expired_freshness_blocks_previously_approved_publication(monkeypatch):
    p, d = ready()
    pid = p["id"]
    approve(pid)
    from app.features.evaluations import service

    current = service.now()
    monkeypatch.setattr(service, "now", lambda: current + timedelta(days=31))
    assert client.get(f"/api/products/{pid}/evaluations").json()[0]["state"] == "stale"
    assert client.post(f"/api/products/{pid}/releases").status_code == 409


def test_processing_exposes_revision_jobs_and_safe_retry():
    p, d = prepared()
    pid = p["id"]
    with SessionLocal() as s:
        rev = s.get(Revision, p["draft"]["id"])
        queue_graph(s, rev)
        s.commit()
    from app.features.graph import service

    original = service.adapter.build

    def fail(build):
        raise RuntimeError("FalkorDB unavailable for this attempt")

    service.adapter.build = fail
    try:
        run_once("test")
    finally:
        service.adapter.build = original
    response = client.get(f"/api/products/{pid}/processing").json()
    job = response["revision_jobs"][0]
    assert job["state"] == "failed"
    assert "FalkorDB unavailable" in job["error"]
    assert job["attempt_count"] == 1
    assert client.post(f"/api/jobs/{job['id']}/retry").status_code == 200
    run_once("test")
    assert client.get(f"/api/products/{pid}/processing").json()["revision_jobs"][0]["state"] == "ready"


def test_graph_recovery_reuses_artifact_after_database_rollback(monkeypatch):
    p, d = prepared()
    pid = p["id"]
    with SessionLocal() as s:
        queue_graph(s, s.get(Revision, p["draft"]["id"]))
        s.commit()
    from app.features.graph import service

    original = service.adapter.build
    keys = []

    def crash_after_external_write(build):
        original(build)
        keys.append(build.graph_key)
        raise RuntimeError("Crash after artifact write")

    monkeypatch.setattr(service.adapter, "build", crash_after_external_write)
    run_once("test")
    with SessionLocal() as s:
        job = s.scalars(select(Job).where(Job.stage == "graph_built")).one()
        job_id = job.id
    assert client.post(f"/api/jobs/{job_id}/retry").status_code == 200

    def recover(build):
        keys.append(build.graph_key)
        original(build)

    monkeypatch.setattr(service.adapter, "build", recover)
    run_once("test")
    assert len(keys) == 2
    assert keys[0] == keys[1]


def test_concurrent_definition_edit_cannot_receive_old_build_pointer(monkeypatch):
    p, d = ready()
    pid = p["id"]
    before = client.get(f"/api/products/{pid}").json()
    client.patch(
        f"/api/products/{pid}",
        json={"expected_generation": before["draft"]["generation"], "purpose": "Changed purpose"},
    )
    with SessionLocal() as s:
        queue_graph(s, s.get(Revision, p["draft"]["id"]))
        s.commit()
    from app.features.graph import service

    original = service.adapter.verify
    entered = Event()
    release = Event()

    def paused_verify(build):
        entered.set()
        assert release.wait(10)
        return original(build)

    monkeypatch.setattr(service.adapter, "verify", paused_verify)
    with ThreadPoolExecutor(2) as pool:
        worker = pool.submit(run_once, "race-worker")
        assert entered.wait(10)
        edit = pool.submit(
            lambda: client.patch(
                f"/api/products/{pid}/ontology",
                json={"kind": "class", "iri": "https://knowledge.example/NewConcept", "label": "New concept"},
            )
        )
        try:
            edit.result(timeout=0.3)
        except TimeoutError:
            pass
        finally:
            release.set()
        assert worker.result(timeout=15)
        assert edit.result(timeout=15).status_code == 200
    assert client.get(f"/api/products/{pid}").json()["draft"]["graph_build_id"] is None


def test_published_revision_lineage_uses_its_manifest_and_consumers():
    p, d = ready()
    pid = p["id"]
    approve(pid)
    old = client.post(f"/api/products/{pid}/releases").json()
    consumer = client.post(
        "/api/consumers",
        json={
            "name": "Pinned app",
            "type": "api",
            "product_id": pid,
            "release_policy": "pinned",
            "release_id": old["id"],
        },
    ).json()
    client.post(f"/api/products/{pid}/draft")
    client.post(f"/api/products/{pid}/graph/build")
    approve(pid)
    new = client.post(f"/api/products/{pid}/releases").json()
    lineage = client.get(f"/api/products/{pid}/lineage?revision_id={old['revision_id']}").json()
    assert lineage["release_id"] == old["id"]
    assert lineage["label"] == "Published evidence trail"
    assert any(n["id"] == consumer["id"] for n in lineage["nodes"])
    assert (
        client.get(f"/api/products/{pid}/lineage?revision_id={new['revision_id']}").json()["release_id"]
        == new["id"]
    )
