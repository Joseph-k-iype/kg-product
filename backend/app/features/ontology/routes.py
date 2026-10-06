from fastapi import APIRouter, Depends, Response, HTTPException
from app.db import get_session
from app.features.products.service import revision
from app.features.ontology import service
from app.features.ontology.schemas import OntologyEdit, ImportInput, MappingInput, SampleInput

router = APIRouter(prefix="/api/products/{id}/ontology")


@router.get("")
def get(id: str, revision_id: str | None = None, session=Depends(get_session, scope="function")):
    return service.details(session, revision(session, id, revision_id))


@router.patch("")
def edit(id: str, input: OntologyEdit, revision_id: str | None = None, session=Depends(get_session, scope="function")):
    return service.save_ontology(session, revision(session, id, revision_id, lock=True), input)


@router.post("/import")
def import_rdf(id: str, input: ImportInput, revision_id: str | None = None, session=Depends(get_session, scope="function")):
    return service.import_ontology(session, revision(session, id, revision_id, lock=True), input)


@router.get("/export")
def export(id: str, revision_id: str | None = None, session=Depends(get_session, scope="function")):
    return Response(
        service.details(session, revision(session, id, revision_id))["turtle"], media_type="text/turtle"
    )


@router.post("/impact")
def impact(id: str, input: ImportInput, revision_id: str | None = None, session=Depends(get_session, scope="function")):
    try:
        return service.impact(session, revision(session, id, revision_id), input.turtle)
    except Exception as e:
        raise HTTPException(422, str(e))


@router.put("/mapping")
def map_rdf(id: str, input: MappingInput, revision_id: str | None = None, session=Depends(get_session, scope="function")):
    return service.save_mapping(session, revision(session, id, revision_id, lock=True), input)


@router.post("/validate-sample")
def validate_sample(
    id: str, input: SampleInput, revision_id: str | None = None, session=Depends(get_session, scope="function")
):
    ontology = service.details(session, revision(session, id, revision_id))["turtle"]
    try:
        return {"findings": service.adapter.validate(ontology, ontology, input.turtle)}
    except Exception as e:
        raise HTTPException(422, str(e))


class StarterInput(SampleInput):
    turtle: str = ""
    template: str = "general"


@router.post("/starter")
def starter(id: str, input: StarterInput, revision_id: str | None = None, session=Depends(get_session, scope="function")):
    from pathlib import Path
    from rdflib.namespace import XSD

    rev = revision(session, id, revision_id, lock=True)
    if input.template == "customer-support":
        turtle = (Path(__file__).parents[2] / "resources/complaints.ttl").read_text()
    elif input.template == "general":
        turtle = """@prefix ex: <https://knowledge.example/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:KnowledgeItem a owl:Class; rdfs:label "Knowledge item"; rdfs:comment "A useful fact supported by a document." .
ex:identifier a owl:DatatypeProperty; rdfs:label "Identifier"; rdfs:domain ex:KnowledgeItem; rdfs:range xsd:string ."""
    else:
        raise HTTPException(422, "Choose a supported starter")
    service.import_ontology(session, rev, ImportInput(turtle=turtle, mode="merge"))
    definitions = service.details(session, rev)
    import re

    classes = [
        {"iri": c["iri"], "label": re.sub("[^A-Za-z0-9_]", "", c["iri"].rsplit("/", 1)[-1])}
        for c in definitions["classes"]
    ]
    properties = [
        {
            "iri": p["iri"],
            "key": "SUBMITTED_BY" if p["iri"].endswith("/submittedBy") else p["iri"].rsplit("/", 1)[-1],
            "kind": p["kind"],
        }
        for p in definitions["properties"]
    ]
    return service.save_mapping(session, rev, MappingInput(classes=classes, properties=properties))


@router.post("/preview-edit")
def preview_edit(id: str, input: OntologyEdit, revision_id: str | None = None, session=Depends(get_session, scope="function")):
    return service.edit_preview(session, revision(session, id, revision_id), input)
