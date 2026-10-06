from fastapi.testclient import TestClient
from app.main import app
from tests.integration.test_governance import ready, approve

client = TestClient(app)


def test_pin_track_lineage_and_overview():
    p, d = ready()
    pid = p["id"]
    approve(pid)
    old = client.post(f"/api/products/{pid}/releases").json()
    pinned = client.post(
        "/api/consumers",
        json={
            "name": "Support copilot",
            "type": "copilot",
            "product_id": pid,
            "release_policy": "pinned",
            "release_id": old["id"],
        },
    ).json()
    tracking = client.post(
        "/api/consumers",
        json={"name": "Service API", "type": "api", "product_id": pid, "release_policy": "active"},
    ).json()
    assert pinned["usage"]["label"] == "Simulated demo usage"
    client.post(f"/api/products/{pid}/draft")
    client.post(f"/api/products/{pid}/graph/build")
    approve(pid)
    new = client.post(f"/api/products/{pid}/releases").json()
    assert client.get(f"/api/consumers/{pinned['id']}/resolve").json()["release_id"] == old["id"]
    assert client.get(f"/api/consumers/{tracking['id']}/resolve").json()["release_id"] == new["id"]
    lineage = client.get(f"/api/products/{pid}/lineage?release_id={old['id']}").json()
    assert any(n["type"] == "document" and n["record_id"] == d["id"] for n in lineage["nodes"])
    assert any(
        n["type"] == "ontology" and n["record_id"] == old["manifest"]["ontology_id"] for n in lineage["nodes"]
    )
    assert any(e["source"] == old["id"] and e["target"] == pinned["id"] for e in lineage["edges"])
    assert client.get("/api/overview").json()["summary"]["active_products"] == 1


def test_consumer_cannot_pin_cross_product_release():
    p, d = ready()
    approve(p["id"])
    r = client.post(f"/api/products/{p['id']}/releases").json()
    other = client.post("/api/products", json={"name": "Other"}).json()
    invalid = client.post(
        "/api/consumers",
        json={
            "name": "Cross product",
            "type": "agent",
            "product_id": other["id"],
            "release_policy": "pinned",
            "release_id": r["id"],
        },
    )
    assert invalid.status_code == 422
