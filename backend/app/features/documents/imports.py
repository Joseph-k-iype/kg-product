import re

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from app.adapters.structured import key
from app.features.ontology import service as ontology
from app.features.ontology.schemas import ImportInput, MappingInput


def prepare_definitions(session, rev, payload):
    """Add definitions and complete mappings, preserving existing identifiers/names."""
    old = ontology.load(session, rev)
    graph = ontology.adapter.parse(payload["definitions"])
    for s, p, o in payload.get("inferred", []):
        subject, predicate, value = URIRef(s), URIRef(p), URIRef(o)
        if (
            predicate == RDF.type
            and value == OWL.Class
            and set(old.objects(subject, RDF.type)) & {OWL.Class, RDFS.Class}
            or predicate == RDFS.range
            and old.value(subject, predicate)
        ):
            graph.remove((subject, predicate, value))
    # Prefix aliases are presentation; retain original IRIs when sources reuse 'ex'.
    old_namespaces = dict(old.namespaces())
    renamed = Graph()
    for prefix, namespace in graph.namespaces():
        if prefix in old_namespaces and old_namespaces[prefix] != namespace:
            prefix = key(prefix + str(namespace))
        renamed.bind(prefix, namespace)
    renamed += graph
    ontology.import_ontology(session, rev, ImportInput(turtle=renamed.serialize(format="turtle")))
    definitions = ontology.details(session, rev)
    existing = definitions["mapping"] or {"classes": [], "properties": []}
    classes = {item["iri"]: item for item in existing["classes"]}
    properties = {item["iri"]: item for item in existing["properties"]}
    labels = {item["label"] for item in classes.values()}
    keys = {item["key"] for item in properties.values()}
    for c in definitions["classes"]:
        if c["iri"] not in classes:
            label = re.sub(r"[^A-Za-z0-9_]", "", c["label"]) or "ImportedRecord"
            if not label[0].isalpha():
                label = "Record" + label
            if label in labels:
                label = key(c["iri"])
            labels.add(label)
            classes[c["iri"]] = {"iri": c["iri"], "label": label}
    for prop in definitions["properties"]:
        if prop["iri"] not in properties:
            name = key(prop["iri"])
            while name in keys:
                name += "_value"
            keys.add(name)
            properties[prop["iri"]] = {"iri": prop["iri"], "key": name, "kind": prop["kind"]}
    ontology.save_mapping(
        session, rev, MappingInput(classes=list(classes.values()), properties=list(properties.values()))
    )
