from urllib.parse import urlparse
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, SH, XSD
from pyshacl import validate

SUPPORTED_OWL = {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.Ontology}
SUPPORTED_SH = {
    SH.NodeShape,
    SH.PropertyShape,
    SH.targetClass,
    SH.property,
    SH.path,
    SH.minCount,
    SH.maxCount,
    SH.datatype,
    SH.ValidationReport,
    SH.ValidationResult,
    SH.conforms,
    SH.result,
    SH.focusNode,
    SH.resultPath,
    SH.resultMessage,
    SH.resultSeverity,
    SH.sourceConstraintComponent,
    SH.sourceShape,
    SH.Violation,
    SH.value,
}


def iri(value: str) -> URIRef:
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https", "urn") or " " in value:
        raise ValueError("Use a stable http, https or urn identifier.")
    return URIRef(value)


class OntologyAdapter:
    def parse(self, turtle: str) -> Graph:
        if len(turtle) > 2 * 1024 * 1024:
            raise ValueError("Definition file exceeds 2 MB")
        return Graph().parse(data=turtle, format="turtle")

    def unsupported(self, g: Graph) -> list[str]:
        found = set()
        for s, p, o in g:
            for term in (p, o):
                if str(term).startswith(str(OWL)) and term not in SUPPORTED_OWL:
                    found.add(str(term))
                if str(term).startswith(str(SH)) and term not in SUPPORTED_SH:
                    found.add(str(term))
        return sorted(found)

    def inspect(self, g: Graph) -> dict:
        def label(n):
            return str(g.value(n, RDFS.label) or str(n).rsplit("/", 1)[-1].rsplit("#", 1)[-1])

        classes = set(g.subjects(RDF.type, OWL.Class)) | set(g.subjects(RDF.type, RDFS.Class))
        props = []
        for kind, type in [("object", OWL.ObjectProperty), ("datatype", OWL.DatatypeProperty)]:
            for node in g.subjects(RDF.type, type):
                props.append(
                    {
                        "iri": str(node),
                        "kind": kind,
                        "label": label(node),
                        "description": str(g.value(node, RDFS.comment) or ""),
                        "domain": str(g.value(node, RDFS.domain) or ""),
                        "range": str(g.value(node, RDFS.range) or ""),
                    }
                )
        shapes = []
        for node in g.subjects(RDF.type, SH.NodeShape):
            for prop in g.objects(node, SH.property):
                shapes.append(
                    {
                        "iri": str(node),
                        "target": str(g.value(node, SH.targetClass) or ""),
                        "path": str(g.value(prop, SH.path) or ""),
                        "min_count": int(g.value(prop, SH.minCount) or 0),
                        "max_count": int(g.value(prop, SH.maxCount))
                        if g.value(prop, SH.maxCount) is not None
                        else None,
                        "datatype": str(g.value(prop, SH.datatype) or ""),
                    }
                )
        return {
            "classes": sorted(
                [
                    {
                        "iri": str(c),
                        "label": label(c),
                        "description": str(g.value(c, RDFS.comment) or ""),
                        "parent": str(g.value(c, RDFS.subClassOf) or ""),
                    }
                    for c in classes
                ],
                key=lambda c: c["label"],
            ),
            "properties": sorted(props, key=lambda p: p["label"]),
            "shapes": shapes,
            "namespaces": [
                {"prefix": p, "iri": str(n)}
                for p, n in g.namespaces()
                if any(str(s).startswith(str(n)) for triple in g for s in triple)
            ],
            "unsupported_constructs": self.unsupported(g),
        }

    def validate(self, ontology: str, shapes: str, instances: str) -> list[dict]:
        definition = self.parse(ontology)
        shape_graph = self.parse(shapes)
        if self.unsupported(shape_graph):
            raise ValueError(
                "Unsupported rules cannot be evaluated. Remove unsupported constructs in Advanced."
            )
        data = self.parse(instances)
        conforms, report, _ = validate(
            data,
            shacl_graph=shape_graph,
            ont_graph=definition,
            inference="none",
            advanced=False,
            js=False,
            do_owl_imports=False,
        )
        findings = []
        for node in report.subjects(RDF.type, SH.ValidationResult):
            findings.append(
                {
                    "entity_id": str(report.value(node, SH.focusNode)),
                    "path": str(report.value(node, SH.resultPath) or ""),
                    "message": str(report.value(node, SH.resultMessage) or "Rule not met"),
                    "shape": str(report.value(node, SH.sourceShape) or ""),
                }
            )
        return findings
