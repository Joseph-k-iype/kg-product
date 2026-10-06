from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH

from app.features.reviews.service import definition_diff
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
EX = "https://rules.example/"
VOCABULARY = """@prefix ex: <https://rules.example/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:Person a owl:Class; rdfs:label "Person"; rdfs:subClassOf ex:Account .
ex:Account a owl:Class; rdfs:label "Account" .
ex:name a owl:DatatypeProperty; rdfs:domain ex:Person; rdfs:range xsd:string .
ex:age a owl:DatatypeProperty; rdfs:domain ex:Person; rdfs:range xsd:integer .
"""


def imported(turtle=VOCABULARY):
    product = client.post("/api/products", json={"name": "Rule regressions"}).json()
    pid = product["id"]
    response = client.post(f"/api/products/{pid}/ontology/import", json={"turtle": turtle})
    assert response.status_code == 200, response.text
    return pid


def exported(pid):
    response = client.get(f"/api/products/{pid}/ontology/export")
    assert response.status_code == 200, response.text
    return Graph().parse(data=response.text, format="turtle")


def test_editing_one_shape_constraint_preserves_siblings():
    pid = imported(
        VOCABULARY
        + """
ex:PersonShape a sh:NodeShape; sh:targetClass ex:Person;
    sh:property [sh:path ex:name; sh:minCount 1];
    sh:property [sh:path ex:age; sh:minCount 1] .
"""
    )
    response = client.patch(
        f"/api/products/{pid}/ontology",
        json={
            "kind": "shape",
            "iri": EX + "PersonShape",
            "target": EX + "Person",
            "path": EX + "name",
            "min_count": 2,
        },
    )
    assert response.status_code == 200, response.text
    graph = exported(pid)
    constraints = {
        str(graph.value(prop, SH.path)): int(graph.value(prop, SH.minCount))
        for prop in graph.objects(URIRef(EX + "PersonShape"), SH.property)
    }
    assert constraints == {EX + "name": 2, EX + "age": 1}
    response = client.patch(
        f"/api/products/{pid}/ontology",
        json={
            "kind": "shape",
            "iri": EX + "PersonShape",
            "target": EX + "Person",
            "path": EX + "nickname",
            "original_path": EX + "name",
            "min_count": 2,
        },
    )
    assert response.status_code == 200, response.text
    graph = exported(pid)
    assert {
        str(graph.value(prop, SH.path)) for prop in graph.objects(URIRef(EX + "PersonShape"), SH.property)
    } == {EX + "nickname", EX + "age"}


def test_review_diff_reports_changes_to_every_constraint_of_one_shape():
    before = {
        "definitions": {
            "shapes": [
                {"iri": EX + "PersonShape", "target": EX + "Person", "path": EX + "name", "min_count": 1},
                {"iri": EX + "PersonShape", "target": EX + "Person", "path": EX + "age", "min_count": 1},
            ]
        }
    }
    after = deepcopy(before)
    after["definitions"]["shapes"][0]["min_count"] = 2
    result = definition_diff(before, after)
    assert result["changed"], result
    changed = result["changed"][0]
    proposed = changed["after"].get("constraints", [changed["after"]])
    assert any(rule["path"] == EX + "name" and rule["min_count"] == 2 for rule in proposed)


@pytest.mark.parametrize(
    "kind, identifier, field, predicate",
    [
        ("class", "Person", "parent", RDFS.subClassOf),
        ("datatype", "name", "domain", RDFS.domain),
        ("datatype", "name", "range", RDFS.range),
    ],
)
def test_explicitly_clearing_definition_links_removes_the_triple(kind, identifier, field, predicate):
    pid = imported()
    subject = URIRef(EX + identifier)
    before = exported(pid)
    assert before.value(subject, predicate) is not None
    # An unrelated partial edit must preserve a link that was omitted.
    response = client.patch(
        f"/api/products/{pid}/ontology",
        json={
            "kind": kind,
            "iri": str(subject),
            "label": "Updated label",
        },
    )
    assert response.status_code == 200, response.text
    assert exported(pid).value(subject, predicate) == before.value(subject, predicate)
    response = client.patch(
        f"/api/products/{pid}/ontology",
        json={
            "kind": kind,
            "iri": str(subject),
            "label": "Updated label",
            field: "",
        },
    )
    assert response.status_code == 200, response.text
    assert exported(pid).value(subject, predicate) is None


@pytest.mark.parametrize("kind", ["object", "datatype"])
def test_rdfs_class_cannot_be_changed_to_a_property(kind):
    pid = imported(VOCABULARY.replace("ex:Person a owl:Class", "ex:Person a rdfs:Class"))
    before = client.get(f"/api/products/{pid}").json()["draft"]
    response = client.patch(
        f"/api/products/{pid}/ontology",
        json={
            "kind": kind,
            "iri": EX + "Person",
            "label": "Person",
        },
    )
    assert response.status_code == 422, response.text
    assert client.get(f"/api/products/{pid}").json()["draft"] == before


def test_label_edit_preserves_the_existing_rdfs_class_kind():
    pid = imported(VOCABULARY.replace("ex:Person a owl:Class", "ex:Person a rdfs:Class"))
    response = client.patch(
        f"/api/products/{pid}/ontology",
        json={
            "kind": "class",
            "iri": EX + "Person",
            "label": "Customer",
        },
    )
    assert response.status_code == 200, response.text
    graph = exported(pid)
    subject = URIRef(EX + "Person")
    assert (subject, RDF.type, RDFS.Class) in graph
    assert (subject, RDF.type, OWL.Class) not in graph


@pytest.mark.parametrize(
    "cardinality",
    [
        'sh:minCount "many"',
        "sh:minCount -1",
        "sh:minCount 1.5",
        "sh:minCount 2; sh:maxCount 1",
        'sh:maxCount "many"',
    ],
)
def test_invalid_supported_shacl_cardinality_is_rejected_without_mutating_draft(cardinality):
    pid = imported()
    before = client.get(f"/api/products/{pid}").json()["draft"]
    response = client.post(
        f"/api/products/{pid}/ontology/import",
        json={
            "turtle": VOCABULARY
            + f"""
ex:PersonShape a sh:NodeShape; sh:targetClass ex:Person;
    sh:property [sh:path ex:name; {cardinality}] .
""",
        },
    )
    assert response.status_code == 422, response.text
    assert client.get(f"/api/products/{pid}").json()["draft"] == before
