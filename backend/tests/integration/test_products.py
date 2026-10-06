from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_product_persistence_and_generation_conflict():
    response = client.post(
        "/api/products",
        json={
            "name": "Customer Complaints",
            "purpose": "Resolve issues",
            "domain": "Service",
            "owner": "Maya Chen",
        },
    )
    assert response.status_code == 201
    product = response.json()
    detail = client.get(f"/api/products/{product['id']}").json()
    assert detail["name"] == "Customer Complaints"
    assert detail["draft"]["generation"] == 1
    updated = client.patch(
        f"/api/products/{product['id']}", json={"expected_generation": 1, "name": "Complaints v2"}
    )
    assert updated.status_code == 200
    stale = client.patch(
        f"/api/products/{product['id']}", json={"expected_generation": 1, "name": "Lost update"}
    )
    assert stale.status_code == 409
    assert client.get(f"/api/products/{product['id']}").json()["name"] == "Complaints v2"


def test_combined_filters_and_pagination():
    client.post(
        "/api/products",
        json={"name": "Payments Search", "purpose": "Payments", "domain": "Finance", "owner": "Leo"},
    )
    result = client.get("/api/products?q=Payments%20Search&domain=Finance&owner=Leo").json()
    assert result["total"] == 1
    assert result["items"][0]["name"] == "Payments Search"


def test_services_report_actual_probe_state():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["probes"] == {"postgres": "ready", "minio": "ready", "falkordb": "ready"}


def test_concurrent_edits_do_not_lose_an_update():
    from concurrent.futures import ThreadPoolExecutor

    p = client.post("/api/products", json={"name": "Concurrent"}).json()

    def change(name):
        return client.patch(
            f"/api/products/{p['id']}", json={"expected_generation": 1, "name": name}
        ).status_code

    with ThreadPoolExecutor(2) as pool:
        statuses = list(pool.map(change, ["First edit", "Second edit"]))
    assert sorted(statuses) == [200, 409]
    assert client.get(f"/api/products/{p['id']}").json()["draft"]["generation"] == 2
