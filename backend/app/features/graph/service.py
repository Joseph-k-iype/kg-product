from uuid import uuid5, NAMESPACE_URL
import json, re
from hashlib import sha256
from sqlalchemy import select
from fastapi import HTTPException
from app.features.products.models import uid
from app.features.products.service import require, mutable
from app.features.graph.models import GraphBuild
from app.features.ontology.models import MappingVersion
from app.features.ontology.service import details
from app.features.documents.models import Chunk, Document
from app.adapters.graph import GraphAdapter
from app.config import settings

adapter = GraphAdapter()


def build_graph(session, rev):
    mutable(rev)
    ontology = details(session, rev)
    if not rev.ontology_id or not rev.mapping_id or not ontology["classes"]:
        raise HTTPException(
            409,
            {
                "code": "concepts_required",
                "message": "Define concepts and representation settings before preparing facts.",
            },
        )
    mapping = require(session, MappingVersion, rev.mapping_id)
    classes = {c["iri"]: c["label"] for c in mapping.definition["classes"]}
    if set(c["iri"] for c in ontology["classes"]) - set(classes):
        raise HTTPException(
            409,
            {
                "code": "unmapped_concepts",
                "message": "Some concepts need representation settings in Advanced.",
            },
        )
    # Revalidate the mapping against the current ontology, including property kinds.
    props = {p["iri"]: p for p in ontology["properties"]}
    if any(
        p["iri"] not in props or props[p["iri"]]["kind"] != p["kind"]
        for p in mapping.definition["properties"]
    ):
        raise HTTPException(409, "Representation settings are stale")
    chunks = session.scalars(
        select(Chunk)
        .join(Document)
        .where(Chunk.revision_id == rev.id, Document.active.is_(True))
        .order_by(Chunk.id)
    ).all()
    docs = session.scalars(
        select(Document).where(
            Document.revision_id == rev.id, Document.active.is_(True), Document.data_kind != "definitions"
        )
    ).all()
    extraction_version = (
        "structured-v1/fixture-rules-v1"
        if any(d.data_kind != "document" for d in docs)
        else "fixture-rules-v1"
    )
    if not chunks or any(not d.extracted_text for d in docs):
        raise HTTPException(409, "Prepare all document excerpts first")
    fingerprint = sha256(
        json.dumps(
            {
                "ontology": rev.ontology_id,
                "mapping": rev.mapping_id,
                "chunks": [c.id for c in chunks],
                "extraction": extraction_version,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    existing = session.scalars(
        select(GraphBuild).where(GraphBuild.revision_id == rev.id, GraphBuild.input_hash == fingerprint)
    ).first()
    if existing and existing.state == "ready":
        adapter.verify(existing)
        rev.graph_build_id = existing.id
        return build_detail(existing)
    nodes = {}
    edges = []
    documents = {d.id: d for d in docs}
    property_keys = {p["iri"]: p["key"] for p in mapping.definition["properties"]}
    property_labels = {p["iri"]: p["label"] for p in ontology["properties"]}
    class_labels = {c["iri"]: c["label"] for c in ontology["classes"]}
    scoped_ids = {}
    for doc in docs:
        if doc.data_kind == "turtle":
            scope = doc.structured_data.get("blank_scope", doc.id)
            scoped_ids[doc.id] = {
                r["id"]: "blank-" + scope + "-" + r["id"] if r.get("blank_node") else r["id"]
                for r in doc.structured_data["records"]
            }
    types = {iri.rsplit("/", 1)[-1]: (iri, label) for iri, label in classes.items()}
    for chunk in chunks:
        evidence = {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "text": chunk.text,
            "start": chunk.start,
            "end": chunk.end,
            "source_url": f"/api/documents/{chunk.document_id}/original",
            "processing_version": chunk.processing_version,
        }
        doc = documents[chunk.document_id]
        if doc.data_kind in ("csv", "json", "turtle"):
            record = doc.structured_data["records"][chunk.ordinal]
            for field in ("source_row", "source_subject"):
                if field in record:
                    evidence[field] = record[field]
            dataset = sha256(
                ((doc.source_id or "local/" + doc.name) + "/" + doc.sha256).encode()
            ).hexdigest()[:20]
            record_id = (
                scoped_ids[doc.id][record["id"]]
                if doc.data_kind == "turtle"
                else "row-" + dataset + "-" + record["id"]
            )
            record_iri = (
                ("urn:knowledge:" + record_id)
                if record.get("blank_node")
                else record.get("iri", "urn:knowledge:" + record_id)
            )
            class_iri = record["class_iris"][0]
            if class_iri not in classes:
                raise HTTPException(409, "Map the imported record concept before preparing knowledge.")
            terms = {property_keys[iri]: values for iri, values in record["values"].items()}
            node = nodes.setdefault(
                record_id,
                {
                    "id": record_id,
                    "iri": record_iri,
                    "type": classes[class_iri],
                    "class_iri": class_iri,
                    "class_iris": record["class_iris"],
                    "type_label": class_labels[class_iri],
                    "label": record["label"],
                    "attributes": {},
                    "attribute_terms": {},
                    "attribute_labels": {
                        property_keys[iri]: property_labels[iri] for iri in record["values"]
                    },
                    "evidence": [],
                    "provenance_label": {
                        "csv": "Imported CSV record",
                        "json": "Imported JSON record",
                        "turtle": "Imported Turtle record",
                    }[doc.data_kind],
                },
            )
            node["class_iris"] = sorted(set(node["class_iris"]) | set(record["class_iris"]))
            for property_key, values in terms.items():
                existing_terms = node["attribute_terms"].setdefault(property_key, [])
                for term in values:
                    if term not in existing_terms:
                        existing_terms.append(term)
                node["attributes"][property_key] = " | ".join(term["value"] for term in existing_terms)
            node["attribute_labels"].update(
                {property_keys[iri]: property_labels[iri] for iri in record["values"]}
            )
            node["evidence"].append(evidence)
            if doc.data_kind == "turtle":
                for edge in doc.structured_data["relationships"]:
                    if edge["source"] == record["id"]:
                        edges.append(
                            {
                                **edge,
                                "source": scoped_ids[doc.id][edge["source"]],
                                "target": scoped_ids[doc.id][edge["target"]],
                                "type": property_keys[edge["iri"]],
                                "evidence": [evidence],
                            }
                        )
            continue
        matches = list(
            re.finditer(r"Complaint\s+(C-\d+)\s+submitted by\s+Customer\s+(A-\d+)", chunk.text, re.I)
        )
        if matches and "Complaint" in types and "Customer" in types:
            for match in matches:
                for kind, id in [("Complaint", match[1]), ("Customer", match[2])]:
                    class_iri, label = types[kind]
                    attrs = {"identifier": id}
                    node = nodes.setdefault(
                        id,
                        {
                            "id": id,
                            "type": label,
                            "iri": "https://knowledge.example/" + id,
                            "class_iri": class_iri,
                            "label": kind + " " + id,
                            "attributes": attrs,
                            "evidence": [],
                        },
                    )
                    if evidence not in node["evidence"]:
                        node["evidence"].append(evidence)
                prop = next(
                    (
                        p
                        for p in mapping.definition["properties"]
                        if p["kind"] == "object" and p["iri"].endswith("/submittedBy")
                    ),
                    None,
                )
                if prop:
                    edges.append(
                        {
                            "source": match[1],
                            "target": match[2],
                            "type": prop["key"],
                            "iri": prop["iri"],
                            "evidence": [evidence],
                        }
                    )
        else:
            class_iri, label = next(iter(classes.items()))
            id = "fact-" + chunk.id
            nodes[id] = {
                "id": id,
                "type": label,
                "iri": "https://knowledge.example/" + id,
                "class_iri": class_iri,
                "label": chunk.text[:90],
                "attributes": {"identifier": id, "excerpt": chunk.text},
                "evidence": [evidence],
            }
    # Collapse overlapping-chunk duplicate edges without losing evidence.
    merged = {}
    for edge in edges:
        key = (edge["source"], edge["target"], edge["type"])
        previous = merged.get(key)
        if previous:
            previous["evidence"] += edge["evidence"]
        else:
            merged[key] = edge
    # Identity survives metadata rollback after external writes; MERGE resumes partial artifacts.
    id = (
        existing.id
        if existing
        else str(
            uuid5(
                NAMESPACE_URL,
                settings.database_url.rsplit("/", 1)[-1]
                + "/"
                + rev.product_id
                + "/"
                + rev.id
                + "/"
                + fingerprint
                + "/"
                + extraction_version,
            )
        )
    )
    build = existing or GraphBuild(
        id=id,
        product_id=rev.product_id,
        revision_id=rev.id,
        generation=rev.generation,
        ontology_id=rev.ontology_id,
        mapping_id=rev.mapping_id,
        input_hash=fingerprint,
        graph_key="kp_"
        + settings.database_url.rsplit("/", 1)[-1]
        + "_"
        + rev.product_id.replace("-", "")
        + "_"
        + rev.id.replace("-", "")
        + "_"
        + id.replace("-", ""),
        extraction_version=extraction_version,
    )
    build.instances = list(nodes.values())
    build.relationships = list(merged.values())
    session.add(build)
    session.flush()
    try:
        adapter.build(build)
    except Exception as e:
        raise HTTPException(503, {"code": "facts_unavailable", "message": str(e)})
    build.state = "ready"
    rev.graph_build_id = build.id
    return build_detail(build)


def build_detail(build):
    return {
        "id": build.id,
        "state": build.state,
        "instance_count": len(build.instances),
        "relationship_count": len(build.relationships),
        "ontology_id": build.ontology_id,
        "mapping_id": build.mapping_id,
        "extraction_version": build.extraction_version,
        "label": "Structured imports and fixture-backed documents"
        if build.extraction_version.startswith("structured")
        else "Fixture-backed extraction",
    }


def resolve_build(session, rev, release=None):
    id = release.manifest["graph_build_id"] if release else rev.graph_build_id
    if not id:
        raise HTTPException(
            409, {"code": "facts_not_prepared", "message": "Prepare knowledge to explore its facts."}
        )
    build = require(session, GraphBuild, id)
    if (
        build.revision_id != rev.id
        or build.product_id != rev.product_id
        or build.state != "ready"
        or build.ontology_id != rev.ontology_id
        or build.mapping_id != rev.mapping_id
    ):
        raise HTTPException(409, "Fact build is unavailable")
    return build


def graph_retrieval(session, rev, query, limit, release=None):
    entities = adapter.search(resolve_build(session, rev, release), query, None, limit)
    return [
        {"entity": e, "evidence": e["evidence"][0] if e["evidence"] else None, "score": None}
        for e in entities
    ]


def graph_context(session, rev, chunk_id, limit, release=None):
    build = resolve_build(session, rev, release)
    matching = [n for n in build.instances if any(e["chunk_id"] == chunk_id for e in n["evidence"])]
    return [adapter.neighbors(build, n["id"], limit) for n in matching[:3]]
