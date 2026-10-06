from fastapi.testclient import TestClient
from rdflib import Graph
from rdflib.compare import isomorphic
from app.main import app

client = TestClient(app)
TURTLE = """@prefix ex: <https://knowledge.example/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
ex:Complaint a owl:Class; rdfs:label "Complaint" .
ex:Customer a owl:Class; rdfs:label "Customer" .
ex:submittedBy a owl:ObjectProperty; rdfs:domain ex:Complaint; rdfs:range ex:Customer .
"""


def product():
    return client.post("/api/products", json={"name": "Concept test"}).json()


def test_rdf_roundtrip_stable_iri_and_invalid_mapping():
    p = product()
    pid = p["id"]
    imported = client.post(f"/api/products/{pid}/ontology/import", json={"turtle": TURTLE, "mode": "merge"})
    assert imported.status_code == 200
    exported = client.get(f"/api/products/{pid}/ontology/export").text
    assert isomorphic(
        Graph().parse(data=TURTLE, format="turtle"), Graph().parse(data=exported, format="turtle")
    )
    edited = client.patch(
        f"/api/products/{pid}/ontology",
        json={
            "kind": "class",
            "iri": "https://knowledge.example/Complaint",
            "label": "Case",
            "description": "A complaint",
        },
    )
    assert edited.status_code == 200
    assert any(
        c["iri"] == "https://knowledge.example/Complaint" and c["label"] == "Case"
        for c in edited.json()["classes"]
    )
    invalid = client.put(
        f"/api/products/{pid}/ontology/mapping",
        json={
            "classes": [{"iri": "https://knowledge.example/Unknown", "label": "Unknown"}],
            "properties": [],
        },
    )
    assert invalid.status_code == 422


def test_replacement_impact_and_namespace_conflicts():
    p = product()
    pid = p["id"]
    client.post(f"/api/products/{pid}/ontology/import", json={"turtle": TURTLE, "mode": "merge"})
    assert (
        client.post(
            f"/api/products/{pid}/ontology/import", json={"turtle": TURTLE, "mode": "replace"}
        ).status_code
        == 409
    )
    conflict = TURTLE.replace("https://knowledge.example/", "https://different.example/")
    assert (
        client.post(
            f"/api/products/{pid}/ontology/import", json={"turtle": conflict, "mode": "merge"}
        ).status_code
        == 422
    )
    preview = client.post(
        f"/api/products/{pid}/ontology/impact", json={"turtle": TURTLE, "mode": "replace"}
    ).json()
    assert (
        client.post(
            f"/api/products/{pid}/ontology/import",
            json={"turtle": TURTLE, "mode": "replace", "impact_token": preview["impact_token"]},
        ).status_code
        == 200
    )


def test_supported_shacl_findings_link_to_instances_and_report_unsupported():
    p = product()
    pid = p["id"]
    client.post(f"/api/products/{pid}/ontology/import", json={"turtle": TURTLE, "mode": "merge"})
    created = client.patch(
        f"/api/products/{pid}/ontology",
        json={
            "kind": "shape",
            "iri": "https://knowledge.example/ComplaintShape",
            "target": "https://knowledge.example/Complaint",
            "path": "https://knowledge.example/identifier",
            "min_count": 1,
            "max_count": 1,
            "datatype": "http://www.w3.org/2001/XMLSchema#string",
        },
    )
    assert created.status_code == 200
    result = client.post(
        f"/api/products/{pid}/ontology/validate-sample",
        json={"turtle": "@prefix ex: <https://knowledge.example/> . ex:C1042 a ex:Complaint ."},
    ).json()
    assert result["findings"][0]["entity_id"] == "https://knowledge.example/C1042"
    imported = client.post(
        f"/api/products/{pid}/ontology/import",
        json={
            "turtle": TURTLE
            + "\n<https://knowledge.example/Complaint> owl:equivalentClass <https://knowledge.example/Customer> .",
            "mode": "merge",
        },
    ).json()
    assert imported["unsupported_constructs"]


def test_merge_rejects_conflicting_meaning_on_a_stable_identifier():
    p = product()
    pid = p["id"]
    client.post(f"/api/products/{pid}/ontology/import", json={"turtle": TURTLE, "mode": "merge"})
    conflicting = TURTLE.replace('rdfs:label "Customer"', 'rdfs:label "Account"')
    result = client.post(
        f"/api/products/{pid}/ontology/import", json={"turtle": conflicting, "mode": "merge"}
    )
    assert result.status_code == 422
    assert result.json()["detail"]["code"] == "definition_conflict"
