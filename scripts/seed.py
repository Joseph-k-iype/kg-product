from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.worker import run_once
from app.db import SessionLocal
from app.features.products.models import Product

client = TestClient(app)
with SessionLocal() as session:
    if session.query(Product).count():
        print(
            "Workspace already has products; seed skipped. Use make reset to start fresh."
        )
        raise SystemExit(0)
products = [
    (
        "HR Policies",
        "Clear, current guidance for every employee.",
        "People",
        "Maya Chen",
        "general",
        "Leave policy: Employees receive 24 days of paid leave each year. Leave requests need manager approval. The notice period is five working days. HR can advise on parental leave and flexible work.",
    ),
    (
        "Payments",
        "Reliable payment and refund guidance for service teams.",
        "Finance",
        "Leo Martin",
        "general",
        "Refunds are available within 30 days of purchase. Payments normally settle in two working days. Failed transactions should be reported to Finance with a transaction identifier.",
    ),
    (
        "Customer Complaints",
        "Help support teams resolve customer issues with verified evidence.",
        "Customer service",
        "Amara Okafor",
        "customer-support",
        "Complaint C-1042 submitted by Customer A-203. Customers can request refunds within 30 days of purchase.\nComplaint C-1043 submitted by Customer A-204. Delivery complaints must be acknowledged within one working day.",
    ),
    (
        "Application Estate",
        "Make application ownership and support easy to find.",
        "Technology",
        "Sam Patel",
        "general",
        "The Customer Portal is owned by Digital Services and supported by the Platform team. Finance owns the Payments application. The service catalog records each application owner and support contact.",
    ),
]
for name, purpose, domain, owner, template, text in products:
    p = client.post(
        "/api/products",
        json={"name": name, "purpose": purpose, "domain": domain, "owner": owner},
    ).json()
    pid = p["id"]
    client.post(f"/api/products/{pid}/ontology/starter", json={"template": template})
    source = client.post(
        "/api/sources",
        json={
            "name": name + " document library",
            "type": "local",
            "owner": owner,
            "location": "Uploaded demo documents",
            "freshness_days": 30,
            "product_ids": [pid],
        },
    ).json()
    d = client.post(
        f"/api/products/{pid}/documents?source_id={source['id']}",
        files={
            "file": (
                name.lower().replace(" ", "-") + ".txt",
                text.encode(),
                "text/plain",
            )
        },
    ).json()
    # Local upload establishes the source's actual freshness.
    from app.features.sources.models import Source
    from app.features.products.models import now

    with SessionLocal() as s:
        s.get(Source, source["id"]).last_synced_at = now()
        s.commit()
    if name == "Payments":
        while run_once("seed-worker"):
            pass
    else:
        client.post(f"/api/products/{pid}/processing/run")
        while run_once("seed-worker"):
            pass
        check = client.post(f"/api/products/{pid}/evaluations").json()
        if check["state"] != "passed":
            raise RuntimeError(check)
        if name in ("HR Policies", "Customer Complaints"):
            review = client.post(
                f"/api/products/{pid}/reviews",
                json={"summary": "Initial synthetic demo knowledge ready for use."},
            ).json()
            if name == "HR Policies":
                client.post(
                    f"/api/reviews/{review['id']}/decision",
                    json={
                        "decision": "approve",
                        "reason": "Demo evidence verified",
                        "reviewer_id": "demo-reviewer",
                    },
                )
                release = client.post(f"/api/products/{pid}/releases").json()
                client.post(
                    "/api/consumers",
                    json={
                        "name": "Employee Copilot",
                        "type": "copilot",
                        "product_id": pid,
                        "release_policy": "active",
                    },
                )
                client.post(
                    "/api/consumers",
                    json={
                        "name": "HR Help API",
                        "type": "api",
                        "product_id": pid,
                        "release_policy": "pinned",
                        "release_id": release["id"],
                    },
                )
print(
    "Four synthetic products seeded with real storage, model vectors and fixture-backed facts."
)
