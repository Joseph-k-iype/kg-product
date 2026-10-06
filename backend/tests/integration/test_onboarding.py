import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_onboarding_creates_a_draft_with_mixed_files_and_a_registered_source():
    metadata = {
        "name": "Mixed knowledge",
        "purpose": "Business evidence",
        "owner": "Maya",
        "domain": "Support",
        "template": "general",
        "config": {"limit": 5},
        "source": {"name": "CRM", "type": "business", "location": "CRM customer workspace"},
    }
    response = client.post(
        "/api/onboarding",
        data={"metadata": json.dumps(metadata)},
        files=[
            ("files", ("customers.csv", b"id,name\n1,Ana\n", "text/csv")),
            ("files", ("policy.txt", b"Refunds are available within thirty days.", "text/plain")),
        ],
    )
    assert response.status_code == 201, response.text
    product = response.json()
    assert product["draft"]["config"]["limit"] == 5
    docs = client.get(f"/api/products/{product['id']}/documents").json()
    assert {d["data_kind"] for d in docs} == {"csv", "document"}
    sources = client.get("/api/sources").json()
    assert sources[0]["product_ids"] == [product["id"]]
    assert sources[0]["connection_state"] == "registered"


def test_invalid_file_leaves_no_partial_product_or_source():
    metadata = {"name": "Must not be saved", "source": {"name": "Source", "type": "external"}}
    r = client.post(
        "/api/onboarding",
        data={"metadata": json.dumps(metadata)},
        files=[
            ("files", ("good.txt", b"Useful knowledge", "text/plain")),
            ("files", ("bad.csv", b"id,id\n1,2", "text/csv")),
        ],
    )
    assert r.status_code == 422, r.text
    assert client.get("/api/products").json()["total"] == 0
    assert client.get("/api/sources").json() == []
