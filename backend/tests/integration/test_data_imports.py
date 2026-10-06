from fastapi.testclient import TestClient

from app.main import app
from app.worker import run_once

client = TestClient(app)
CSV = b'\xef\xbb\xbfid,name,notes\r\n1,Ana,"Refund requested, urgent"\r\n2,Ben,"Two\nlines"\r\n'
TTL = b"""@prefix ex: <https://records.example/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:Customer a owl:Class; rdfs:label "Customer" .
ex:age a owl:DatatypeProperty; rdfs:domain ex:Customer; rdfs:range xsd:integer .
ex:knows a owl:ObjectProperty; rdfs:domain ex:Customer; rdfs:range ex:Customer .
ex:ana a ex:Customer; rdfs:label "Ana"; ex:age 34; ex:knows ex:ben .
ex:ben a ex:Customer; rdfs:label "Ben"; ex:age 29 ."""


def product():
    return client.post(
        "/api/products",
        json={
            "name": "Structured knowledge",
            "purpose": "Customer records",
            "domain": "Support",
            "owner": "Maya Chen",
        },
    ).json()


def process():
    for _ in range(15):
        if not run_once("import-test"):
            break


def test_csv_preview_preserves_quoted_cells_and_reports_records():
    r = client.post("/api/imports/preview", files={"file": ("customers.csv", CSV, "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["record_count"] == 2
    assert r.json()["columns"] == ["id", "name", "notes"]
    assert r.json()["sample_rows"][1]["notes"] == "Two\nlines"


def test_invalid_csv_and_turtle_are_rejected_before_draft_changes():
    p = product()
    for name, data in [
        ("bad.csv", b"id,id\n1,2"),
        ("ragged.csv", b"id,name\n1,Ana,extra"),
        ("empty.csv", b"id,name\n"),
        ("bad.ttl", b"not valid turtle"),
    ]:
        r = client.post(
            f"/api/products/{p['id']}/documents", files={"file": (name, data, "application/octet-stream")}
        )
        assert r.status_code == 422, r.text
    assert client.get(f"/api/products/{p['id']}/documents").json() == []
    assert client.get(f"/api/products/{p['id']}").json()["draft"]["generation"] == p["draft"]["generation"]


def test_csv_rows_become_distinct_cited_records_and_keep_original():
    p = product()
    r = client.post(f"/api/products/{p['id']}/documents", files={"file": ("customers.csv", CSV, "text/csv")})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["data_kind"] == "csv"
    process()
    detail = client.get(f"/api/documents/{d['id']}").json()
    assert len(detail["chunks"]) == 2
    assert "Two\nlines" in detail["chunks"][1]["text"]
    assert client.get(f"/api/documents/{d['id']}/original").content == CSV
    assert client.post(f"/api/products/{p['id']}/graph/build").status_code == 200
    entities = client.get(f"/api/products/{p['id']}/entities").json()["items"]
    assert len(entities) == 2
    ana = next(n for n in entities if n["label"] == "Ana")
    assert ana["provenance_label"] == "Imported CSV record"
    assert ana["evidence"][0]["source_row"] == 1
    assert ana["evidence"][0]["document_id"] == d["id"]


def test_turtle_imports_definitions_instances_relationships_and_typed_values():
    p = product()
    preview = client.post("/api/imports/preview", files={"file": ("records.ttl", TTL, "text/turtle")})
    assert preview.status_code == 200, preview.text
    assert preview.json()["record_count"] == 2
    assert preview.json()["concept_count"] == 1
    r = client.post(f"/api/products/{p['id']}/documents", files={"file": ("records.ttl", TTL, "text/turtle")})
    assert r.status_code == 201, r.text
    process()
    built = client.post(f"/api/products/{p['id']}/graph/build")
    assert built.status_code == 200, built.text
    assert built.json()["instance_count"] == 2
    assert built.json()["relationship_count"] == 1
    nodes = client.get(f"/api/products/{p['id']}/entities").json()["items"]
    ana = next(n for n in nodes if n["label"] == "Ana")
    assert ana["iri"] == "https://records.example/ana"
    assert ana["provenance_label"] == "Imported Turtle record"
    assert ana["evidence"][0]["source_subject"] == ana["iri"]
    definitions = client.get(f"/api/products/{p['id']}/ontology").json()
    assert len(definitions["classes"]) == 1
    assert {p["iri"] for p in definitions["mapping"]["properties"]} == {
        "https://records.example/age",
        "https://records.example/knows",
        "http://www.w3.org/2000/01/rdf-schema#label",
    }


def test_definition_only_turtle_is_stored_without_fabricating_records():
    p = product()
    data = b"@prefix ex: <https://terms.example/> . @prefix owl: <http://www.w3.org/2002/07/owl#> . ex:Policy a owl:Class ."
    r = client.post(
        f"/api/products/{p['id']}/documents", files={"file": ("concepts.ttl", data, "text/turtle")}
    )
    assert r.status_code == 201, r.text
    assert r.json()["data_kind"] == "definitions"
    process()
    assert client.get(f"/api/documents/{r.json()['id']}").json()["chunks"] == []
    assert client.post(f"/api/products/{p['id']}/graph/build").status_code == 409


def test_turtle_labels_comments_language_tags_and_typed_literals_reach_quality_checks():
    p = product()
    data = (
        TTL
        + b"""\n@prefix sh: <http://www.w3.org/ns/shacl#> .
ex:ana rdfs:label "Anne"@fr; rdfs:comment "Customer account"@en .
ex:ben rdfs:comment "Customer account"@en .
ex:CustomerShape a sh:NodeShape; sh:targetClass ex:Customer;
  sh:property [sh:path rdfs:label; sh:minCount 1];
  sh:property [sh:path rdfs:comment; sh:minCount 1];
  sh:property [sh:path ex:age; sh:datatype xsd:integer] ."""
    )
    uploaded = client.post(
        f"/api/products/{p['id']}/documents", files={"file": ("customers.ttl", data, "text/turtle")}
    )
    assert uploaded.status_code == 201, uploaded.text
    process()
    assert client.post(f"/api/products/{p['id']}/graph/build").status_code == 200
    result = client.post(f"/api/products/{p['id']}/evaluations").json()
    assert next(metric for metric in result["metrics"] if metric["key"] == "rules")["state"] == "passed", (
        result["findings"]
    )


def test_independent_blank_nodes_are_scoped_to_their_imported_file():
    p = product()
    data = b'@prefix ex: <https://records.example/> . [] a ex:Person; ex:name "Ana" .'
    for name in ("first.ttl", "second.ttl"):
        r = client.post(f"/api/products/{p['id']}/documents", files={"file": (name, data, "text/turtle")})
        assert r.status_code == 201, r.text
    process()
    r = client.post(f"/api/products/{p['id']}/graph/build")
    assert r.status_code == 200, r.text
    assert r.json()["instance_count"] == 2
    nodes = client.get(f"/api/products/{p['id']}/entities").json()["items"]
    assert len({node["iri"] for node in nodes}) == 2


def test_instance_only_turtle_reuses_existing_class_labels_and_rdfs_kind():
    p = product()
    vocabulary = b'@prefix ex: <https://records.example/> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> . ex:Customer a rdfs:Class; rdfs:label "Customer account" .'
    assert (
        client.post(
            f"/api/products/{p['id']}/documents",
            files={"file": ("vocabulary.ttl", vocabulary, "text/turtle")},
        ).status_code
        == 201
    )
    r = client.post(
        f"/api/products/{p['id']}/documents",
        files={
            "file": (
                "customers.ttl",
                b'@prefix ex: <https://records.example/> . ex:ana a ex:Customer; ex:name "Ana" .',
                "text/turtle",
            )
        },
    )
    assert r.status_code == 201, r.text
    definitions = client.get(f"/api/products/{p['id']}/ontology").json()
    assert definitions["classes"][0]["label"] == "Customer account"


def test_instance_only_turtle_infers_relationship_mapping_for_named_and_blank_targets():
    p = product()
    data = b'@prefix ex: <https://records.example/> . ex:ana a ex:Person; ex:knows [a ex:Person; ex:name "Ben"] .'
    r = client.post(f"/api/products/{p['id']}/documents", files={"file": ("people.ttl", data, "text/turtle")})
    assert r.status_code == 201, r.text
    process()
    built = client.post(f"/api/products/{p['id']}/graph/build")
    assert built.status_code == 200, built.text
    assert built.json()["instance_count"] == 2
    assert built.json()["relationship_count"] == 1
