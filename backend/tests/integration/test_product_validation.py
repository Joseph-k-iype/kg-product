import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

INVALID_CONFIGS = [
    {"quality_gates": None},
    {"quality_gates": []},
    {"quality_gates": {"freshness": "many"}},
    {"quality_gates": {"freshness": 2}},
    {"quality_gates": {"freshness": True}},
    {"embedding_model": {"name": "model"}},
    {"embedding_model": {"name": "model", "revision": "version", "dimension": "bad"}},
    {"limit": 0},
]


@pytest.mark.parametrize("config", INVALID_CONFIGS)
def test_invalid_configuration_cannot_be_persisted(config):
    assert client.post("/api/products", json={"name": "Invalid config", "config": config}).status_code == 422
    product = client.post("/api/products", json={"name": "Valid config"}).json()
    updated = client.patch(f"/api/products/{product['id']}", json={"expected_generation": 1, "config": config})
    assert updated.status_code == 422
    assert client.get(f"/api/products/{product['id']}").json()["draft"]["generation"] == 1
    assert client.post(f"/api/products/{product['id']}/evaluations").status_code == 200


def test_invalid_search_model_returns_validation_error_instead_of_server_error():
    product = client.post("/api/products", json={"name": "Search inputs"}).json()
    response = client.post(f"/api/products/{product['id']}/retrieval", json={"query": "refund", "preview": True, "model": {"name": "model"}})
    assert response.status_code == 422


def test_product_edit_rejects_whitespace_name():
    product = client.post("/api/products", json={"name": "Valid name"}).json()
    assert client.patch(f"/api/products/{product['id']}", json={"expected_generation": 1, "name": "   "}).status_code == 422
    assert client.get(f"/api/products/{product['id']}").json()["name"] == "Valid name"


def test_quality_completeness_does_not_count_whitespace_as_business_details():
    product = client.post("/api/products", json={"name": "Metadata requirements", "purpose": "   "}).json()
    evaluation = client.post(f"/api/products/{product['id']}/evaluations").json()
    metadata = next(metric for metric in evaluation["metrics"] if metric["key"] == "metadata")
    assert metadata["value"] == 0.75
    assert metadata["state"] == "failed"
