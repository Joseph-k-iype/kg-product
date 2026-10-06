from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.worker import run_once
import pytest

client = TestClient(app)


@pytest.mark.parametrize("filename", ["support-policy.pdf", "application-estate.docx"])
def test_supported_document_format_original_and_extracted_text(filename):
    p = client.post("/api/products", json={"name": "Formats " + filename}).json()
    data = Path("../fixtures/documents/" + filename).read_bytes()
    d = client.post(
        f"/api/products/{p['id']}/documents", files={"file": (filename, data, "application/octet-stream")}
    ).json()
    run_once("format-worker")
    run_once("format-worker")
    result = client.get(f"/api/documents/{d['id']}").json()
    assert "30 days" in result["extracted_text"]
    response = client.get(f"/api/documents/{d['id']}/original")
    assert response.content == data
    assert response.headers["x-content-type-options"] == "nosniff"


def test_text_upload_cannot_publish_active_html():
    p = client.post("/api/products", json={"name": "Safe originals"}).json()
    d = client.post(
        f"/api/products/{p['id']}/documents",
        files={"file": ("unsafe.txt", b"<script>alert(1)</script>", "text/html")},
    ).json()
    response = client.get(f"/api/documents/{d['id']}/original")
    assert response.headers["content-type"].startswith("text/plain")
