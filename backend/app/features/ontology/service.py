import json, re
from hashlib import sha256
from sqlalchemy import select, func
from fastapi import HTTPException
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, SH, XSD
from app.features.ontology.models import OntologyVersion, MappingVersion
from app.features.products.service import touch, require
from app.adapters.ontology import OntologyAdapter, iri
from app.adapters.storage import ObjectStore
from app.domain.contracts import ArtifactRef

adapter = OntologyAdapter()


def load(session, rev):
    if not rev.ontology_id:
        return Graph()
    version = require(session, OntologyVersion, rev.ontology_id)
    return adapter.parse(
        ObjectStore().get(ArtifactRef(version.object_key, version.sha256, str(version.version))).decode()
    )


def details(session, rev):
    graph = load(session, rev)
    data = adapter.inspect(graph)
    version = session.get(OntologyVersion, rev.ontology_id) if rev.ontology_id else None
    mapping = session.get(MappingVersion, rev.mapping_id) if rev.mapping_id else None
    return {
        **data,
        "id": rev.ontology_id,
        "version": version.version if version else 0,
        "generation": rev.generation,
        "turtle": graph.serialize(format="turtle"),
        "mapping": {
            "id": mapping.id,
            "version": mapping.version,
            "classes": mapping.definition.get("classes", []),
            "properties": mapping.definition.get("properties", []),
        }
        if mapping
        else None,
    }


def persist(session, rev, graph, expected=None):
    touch(session, rev, "Concepts and rules updated", expected)
    canonical = graph.serialize(format="turtle")
    artifact = ObjectStore().put(canonical.encode(), "text/turtle")
    number = (
        session.scalar(
            select(func.max(OntologyVersion.version)).where(OntologyVersion.product_id == rev.product_id)
        )
        or 0
    ) + 1
    version = OntologyVersion(
        product_id=rev.product_id,
        revision_id=rev.id,
        version=number,
        object_key=artifact.key,
        sha256=artifact.sha256,
        unsupported=adapter.unsupported(graph),
    )
    session.add(version)
    session.flush()
    rev.ontology_id = version.id
    return details(session, rev)


def impact(session, rev, proposed):
    graph = load(session, rev)
    before = set(
        adapter.inspect(graph)["classes"][i]["iri"] for i in range(len(adapter.inspect(graph)["classes"]))
    )
    after = set(c["iri"] for c in adapter.inspect(adapter.parse(proposed))["classes"])
    mapping = session.get(MappingVersion, rev.mapping_id) if rev.mapping_id else None
    payload = {
        "revision": rev.id,
        "generation": rev.generation,
        "ontology": rev.ontology_id,
        "proposed": sha256(proposed.encode()).hexdigest(),
    }
    token = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {
        "impact_token": token,
        "removed_concepts": sorted(before - after),
        "affected_mappings": mapping.definition if mapping else {},
        "rebuild_steps": ["Prepare knowledge", "Run quality checks", "Request new approval"],
        "published_data_preserved": True,
    }


def import_ontology(session, rev, input):
    try:
        new = adapter.parse(input.turtle)
        old = load(session, rev)
    except Exception as e:
        raise HTTPException(422, {"code": "invalid_definitions", "message": str(e)})
    if input.mode == "replace":
        if input.impact_token != impact(session, rev, input.turtle)["impact_token"]:
            raise HTTPException(
                409,
                {
                    "code": "impact_required",
                    "message": "Preview how replacing concepts affects this product first.",
                },
            )
        return persist(session, rev, new, input.expected_generation)
    old_ns = dict(old.namespaces())
    for prefix, ns in new.namespaces():
        if prefix in old_ns and old_ns[prefix] != ns:
            raise HTTPException(
                422,
                {
                    "code": "namespace_conflict",
                    "message": f"Prefix {prefix} already identifies a different vocabulary.",
                },
            )
        old.bind(prefix, ns, replace=True)
    for subject in set(new.subjects()):
        old_kinds = set(old.objects(subject, RDF.type))
        new_kinds = set(new.objects(subject, RDF.type))
        types = {OWL.Class, RDFS.Class, OWL.ObjectProperty, OWL.DatatypeProperty}
        if old_kinds & types and new_kinds & types and old_kinds & types != new_kinds & types:
            raise HTTPException(422, "Identifier has conflicting concept/property kinds")
    for subject in set(new.subjects()):
        for predicate in [RDFS.label, RDFS.comment, RDFS.subClassOf, RDFS.domain, RDFS.range, SH.targetClass]:
            old_values = set(old.objects(subject, predicate))
            new_values = set(new.objects(subject, predicate))
            if old_values and new_values and old_values != new_values:
                raise HTTPException(
                    422,
                    {
                        "code": "definition_conflict",
                        "message": "This import changes an existing definition. Use the guided editor or replacement with an impact preview.",
                    },
                )
    old += new
    return persist(session, rev, old, input.expected_generation)


def proposed_edit(session, rev, edit):
    g = load(session, rev)
    try:
        node = iri(edit.iri)
        if edit.kind == "namespace":
            namespaces = dict(g.namespaces())
            if edit.prefix in namespaces and namespaces[edit.prefix] != node:
                raise ValueError("Namespace prefix already exists")
            g.bind(edit.prefix, node, replace=True)
        elif edit.kind == "delete":
            proposed = Graph()
            proposed += g
            proposed.remove((node, None, None))
            serialized = proposed.serialize(format="turtle")
            g = proposed
        elif edit.kind == "shape":
            if not (node, RDF.type, SH.NodeShape) in g:
                g.add((node, RDF.type, SH.NodeShape))
            if (iri(edit.target), RDF.type, OWL.Class) not in g and (
                iri(edit.target),
                RDF.type,
                RDFS.Class,
            ) not in g:
                raise ValueError("Choose an existing target concept")
            if edit.max_count is not None and edit.min_count > edit.max_count:
                raise ValueError("Minimum cannot exceed maximum")
            g.set((node, SH.targetClass, iri(edit.target)))
            for previous in list(g.objects(node, SH.property)):
                g.remove((previous, None, None))
            g.remove((node, SH.property, None))
            prop = BNode()
            g.add((node, SH.property, prop))
            g.add((prop, SH.path, iri(edit.path)))
            g.add((prop, SH.minCount, Literal(edit.min_count, datatype=XSD.integer)))
            if edit.max_count is not None:
                g.add((prop, SH.maxCount, Literal(edit.max_count, datatype=XSD.integer)))
            if edit.datatype:
                g.add((prop, SH.datatype, iri(edit.datatype)))
        else:
            type = {"class": OWL.Class, "object": OWL.ObjectProperty, "datatype": OWL.DatatypeProperty}[
                edit.kind
            ]
            existing = set(g.objects(node, RDF.type)) & {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty}
            if existing and type not in existing:
                raise ValueError("An identifier cannot change concept/property kind")
            g.add((node, RDF.type, type))
            g.set((node, RDFS.label, Literal(edit.label or edit.iri.rsplit("/", 1)[-1])))
            g.set((node, RDFS.comment, Literal(edit.description)))
            if edit.parent:
                g.set((node, RDFS.subClassOf, iri(edit.parent)))
            if edit.domain:
                g.set((node, RDFS.domain, iri(edit.domain)))
            if edit.range:
                g.set((node, RDFS.range, iri(edit.range)))
        return g
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(422, {"code": "invalid_concept", "message": str(e)})


def edit_preview(session, rev, edit):
    from rdflib.compare import to_canonical_graph

    proposed = proposed_edit(session, rev, edit)
    serialized = proposed.serialize(format="turtle")
    from app.features.graph.models import GraphBuild

    builds = session.scalars(select(GraphBuild).where(GraphBuild.product_id == rev.product_id)).all()
    affected = set()
    existing_graph = load(session, rev)
    old_target = existing_graph.value(URIRef(edit.iri), SH.targetClass)
    for build in builds:
        for node in build.instances:
            if node["class_iri"] == edit.iri or (old_target and node["class_iri"] == str(old_target)):
                affected.add(node["id"])
            mapping = session.get(MappingVersion, build.mapping_id)
            matching = [
                p["key"]
                for p in mapping.definition["properties"]
                if p["iri"] == edit.iri and p["kind"] == "datatype"
            ]
            if any(key in node["attributes"] for key in matching):
                affected.add(node["id"])
        for edge in build.relationships:
            if edge.get("iri") == edit.iri:
                affected.add(edge["source"])
    canonical = to_canonical_graph(proposed)
    digest = sha256(
        "\n".join(sorted(" ".join(t.n3() for t in triple) for triple in canonical)).encode()
    ).hexdigest()
    token = sha256(
        json.dumps(
            {
                "revision": rev.id,
                "generation": rev.generation,
                "ontology": rev.ontology_id,
                "proposed": digest,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return {
        **impact(session, rev, serialized),
        "impact_token": token,
        "affected_instance_count": len(affected),
        "proposed_turtle": serialized,
    }


def save_ontology(session, rev, edit):
    preview = edit_preview(session, rev, edit)
    if preview["affected_instance_count"] and preview["impact_token"] != edit.impact_token:
        raise HTTPException(
            409,
            {
                "code": "impact_required",
                "message": "Review the impact on existing facts before changing this definition.",
                **preview,
            },
        )
    if edit.kind == "delete" and preview["impact_token"] != edit.impact_token:
        raise HTTPException(
            409,
            {
                "code": "impact_required",
                "message": "Preview affected definitions before removing a concept.",
                **preview,
            },
        )
    return persist(session, rev, proposed_edit(session, rev, edit), edit.expected_generation)


def save_mapping(session, rev, input):
    graph = load(session, rev)
    definition = adapter.inspect(graph)
    classes = {c["iri"] for c in definition["classes"]}
    properties = {p["iri"]: p for p in definition["properties"]}
    labels = set()
    keys = set()
    mapped = set()
    for item in input.classes:
        if (
            item.get("iri") not in classes
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", item.get("label", ""))
            or item["label"] in labels
            or item["iri"] in mapped
        ):
            raise HTTPException(
                422,
                {
                    "code": "invalid_mapping",
                    "message": "Choose existing concepts with unique valid fact type names.",
                },
            )
        labels.add(item["label"])
        mapped.add(item["iri"])
    for item in input.properties:
        prop = properties.get(item.get("iri"))
        key = item.get("key", "")
        if (
            not prop
            or prop["kind"] != item.get("kind")
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key)
            or key in keys
        ):
            raise HTTPException(
                422,
                {
                    "code": "invalid_mapping",
                    "message": "Attribute or relationship mapping is invalid or conflicts.",
                },
            )
        if prop["domain"] and prop["domain"] not in mapped:
            raise HTTPException(422, "Map the property target concept first")
        if prop["kind"] == "object" and prop["range"] not in mapped:
            raise HTTPException(422, "Map the relationship destination concept first")
        keys.add(key)
    touch(session, rev, "Representation settings updated", input.expected_generation)
    number = (
        session.scalar(
            select(func.max(MappingVersion.version)).where(MappingVersion.product_id == rev.product_id)
        )
        or 0
    ) + 1
    mapping = MappingVersion(
        product_id=rev.product_id,
        revision_id=rev.id,
        ontology_id=rev.ontology_id,
        version=number,
        definition={"classes": input.classes, "properties": input.properties},
    )
    session.add(mapping)
    session.flush()
    rev.mapping_id = mapping.id
    return details(session, rev)
