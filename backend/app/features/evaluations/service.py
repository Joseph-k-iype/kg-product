from datetime import timedelta
import json
from hashlib import sha256
from sqlalchemy import select
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, XSD
from fastapi import HTTPException
from app.features.products.service import require
from app.features.products.models import Product, now
from app.features.documents.models import Document, Chunk
from app.features.ontology.models import OntologyVersion, MappingVersion
from app.features.graph.models import GraphBuild
from app.features.ontology.service import details, adapter
from app.features.sources.models import Source
from app.features.evaluations.models import EvaluationRun
from app.features.retrieval.service import default_model
from dataclasses import asdict


def source_freshness(session, docs):
    inputs = []
    for doc in docs:
        source = session.get(Source, doc.source_id) if doc.source_id else None
        updated = source.last_synced_at if source else doc.uploaded_at
        days = source.freshness_days if source else 30
        deadline = updated + timedelta(days=days) if updated else None
        inputs.append(
            {
                "document_id": doc.id,
                "source_id": doc.source_id,
                "updated_at": updated.isoformat() if updated else None,
                "deadline": deadline.isoformat() if deadline else None,
                "freshness_days": days,
                "fresh": now() <= deadline if deadline else None,
            }
        )
    return inputs


def snapshot(session, rev):
    product = require(session, Product, rev.product_id)
    docs = session.scalars(
        select(Document)
        .where(Document.revision_id == rev.id, Document.active.is_(True))
        .order_by(Document.id)
    ).all()
    chunks = session.scalars(
        select(Chunk)
        .join(Document)
        .where(Chunk.revision_id == rev.id, Document.active.is_(True))
        .order_by(Chunk.id)
    ).all()
    ontology = session.get(OntologyVersion, rev.ontology_id) if rev.ontology_id else None
    definitions = details(session, rev)
    return {
        "product_id": rev.product_id,
        "revision_id": rev.id,
        "generation": rev.generation,
        "metadata": {
            "name": product.name,
            "purpose": product.purpose,
            "domain": product.domain,
            "owner": product.owner,
            "tags": product.tags,
        },
        "config": rev.config,
        "ontology_id": rev.ontology_id,
        "ontology_sha256": ontology.sha256 if ontology else None,
        "mapping_id": rev.mapping_id,
        "graph_build_id": rev.graph_build_id,
        "definitions": {key: definitions[key] for key in ["classes", "properties", "shapes", "namespaces"]},
        "mapping_definition": session.get(MappingVersion, rev.mapping_id).definition
        if rev.mapping_id
        else None,
        "freshness_inputs": source_freshness(session, docs),
        "documents": [
            {
                "id": d.id,
                "name": d.name,
                "sha256": d.sha256,
                "object_key": d.object_key,
                "extracted_key": d.extracted_key,
                "extracted_sha256": d.extracted_sha256,
                "source_id": d.source_id,
                "processing_version": d.processing_version,
            }
            for d in docs
        ],
        "chunks": [
            {
                "id": c.id,
                "document_id": c.document_id,
                "start": c.start,
                "end": c.end,
                "text_sha256": sha256(c.text.encode()).hexdigest(),
                "embedded": c.embedding is not None,
                "model_name": c.model_name,
                "model_revision": c.model_revision,
                "model_dimension": c.model_dimension,
            }
            for c in chunks
        ],
    }


def fingerprint(inputs):
    return sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()


def run_detail(session, run, rev):
    current = run.input_hash == fingerprint(snapshot(session, rev))
    return {
        "id": run.id,
        "revision_id": run.revision_id,
        "generation": run.generation,
        "state": run.state if current else "stale",
        "metrics": run.metrics,
        "findings": run.findings,
        "inputs": run.inputs,
        "created_at": run.created_at,
    }


def evaluate(session, rev):
    inputs = snapshot(session, rev)
    docs = session.scalars(
        select(Document).where(Document.revision_id == rev.id, Document.active.is_(True))
    ).all()
    chunks = session.scalars(
        select(Chunk).join(Document).where(Chunk.revision_id == rev.id, Document.active.is_(True))
    ).all()
    ontology = details(session, rev)
    build = session.get(GraphBuild, rev.graph_build_id) if rev.graph_build_id else None
    metrics = []
    findings = []
    gates = rev.config.get("quality_gates", {})

    def metric(key, label, value, default=1.0):
        threshold = float(gates.get(key, default))
        if threshold < 0 or threshold > 1:
            raise HTTPException(422, "Quality thresholds must be between 0 and 1")
        state = "insufficient_data" if value is None else ("passed" if value >= threshold else "failed")
        metrics.append({"key": key, "label": label, "value": value, "threshold": threshold, "state": state})
        if state != "passed":
            findings.append(
                {
                    "id": key,
                    "message": label
                    + (" needs input" if value is None else " is below the required threshold"),
                    "url": f"/products/{rev.product_id}/"
                    + (
                        "sources"
                        if key in ("freshness", "extraction")
                        else "concepts"
                        if key in ("mapping", "rules")
                        else "processing"
                        if key == "embeddings"
                        else "health"
                    ),
                }
            )

    fresh = [entry["fresh"] for entry in inputs["freshness_inputs"]]
    metric(
        "freshness",
        "Sources up to date",
        sum(fresh) / len(fresh) if fresh and all(value is not None for value in fresh) else None,
    )
    metric(
        "extraction",
        "Documents readable",
        sum(d.extracted_text is not None for d in docs) / len(docs) if docs else None,
    )
    metadata = inputs["metadata"]
    metric(
        "metadata",
        "Product details complete",
        sum(bool(metadata[k]) for k in ["name", "purpose", "owner", "domain"]) / 4,
    )
    model = rev.config.get("embedding_model", asdict(default_model()))
    metric(
        "embeddings",
        "Documents searchable",
        sum(
            c.embedding is not None
            and (c.model_name, c.model_revision, c.model_dimension)
            == (model["name"], model["revision"], model["dimension"])
            for c in chunks
        )
        / len(chunks)
        if chunks
        else None,
    )
    mapping = ontology["mapping"]
    defined = {c["iri"] for c in ontology["classes"]} | {p["iri"] for p in ontology["properties"]}
    mapped = {c["iri"] for c in (mapping["classes"] if mapping else [])} | {
        p["iri"] for p in (mapping["properties"] if mapping else [])
    }
    metric("mapping", "Concepts ready to use", len(defined & mapped) / len(defined) if defined else None)
    rule_value = None
    if (
        build
        and build.state == "ready"
        and build.ontology_id == rev.ontology_id
        and build.mapping_id == rev.mapping_id
    ):
        try:
            graph = Graph()
            keys = {p["key"]: p["iri"] for p in mapping["properties"] if p["kind"] == "datatype"}
            for n in build.instances:
                subject = URIRef(n["iri"])
                for class_iri in n.get("class_iris", [n["class_iri"]]):
                    graph.add((subject, RDF.type, URIRef(class_iri)))
                for key, value in n["attributes"].items():
                    if key in keys:
                        if key in n.get("attribute_terms", {}):
                            for term in n["attribute_terms"][key]:
                                graph.add(
                                    (
                                        subject,
                                        URIRef(keys[key]),
                                        Literal(
                                            term["value"],
                                            datatype=URIRef(term["datatype"]) if term["datatype"] else None,
                                            lang=term["language"],
                                        ),
                                    )
                                )
                        else:
                            graph.add((subject, URIRef(keys[key]), Literal(value, datatype=XSD.string)))
            for r in build.relationships:
                a = next(n for n in build.instances if n["id"] == r["source"])
                b = next(n for n in build.instances if n["id"] == r["target"])
                graph.add((URIRef(a["iri"]), URIRef(r["iri"]), URIRef(b["iri"])))
            violations = adapter.validate(
                ontology["turtle"], ontology["turtle"], graph.serialize(format="turtle")
            )
            violating = {f["entity_id"] for f in violations}
            rule_value = 1 - len(violating) / len(build.instances) if build.instances else None
            for f in violations:
                findings.append({**f, "url": f"/products/{rev.product_id}/explorer", "message": f["message"]})
        except Exception as e:
            findings.append({"message": str(e), "url": f"/products/{rev.product_id}/concepts"})
    metric("rules", "Business rules met", rule_value)
    citations = (
        sum(bool(n["evidence"]) for n in build.instances) / len(build.instances)
        if build and build.instances
        else None
    )
    metric("citations", "Facts supported by evidence", citations)
    states = {m["state"] for m in metrics}
    state = (
        "insufficient_data" if "insufficient_data" in states else "failed" if "failed" in states else "passed"
    )
    run = EvaluationRun(
        product_id=rev.product_id,
        revision_id=rev.id,
        generation=rev.generation,
        input_hash=fingerprint(inputs),
        inputs=inputs,
        metrics=metrics,
        findings=findings,
        state=state,
    )
    session.add(run)
    session.flush()
    return run_detail(session, run, rev)


def current_pass(session, rev):
    run = session.scalars(
        select(EvaluationRun)
        .where(EvaluationRun.revision_id == rev.id)
        .order_by(EvaluationRun.created_at.desc())
    ).first()
    if not run or run.state != "passed" or run.input_hash != fingerprint(snapshot(session, rev)):
        raise HTTPException(
            409,
            {
                "code": "current_checks_required",
                "message": "Run current quality checks and resolve all required issues before requesting approval.",
            },
        )
    return run
