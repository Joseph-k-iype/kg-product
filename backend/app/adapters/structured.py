"""Normalize imported records without treating them as fixture-extracted text."""

import csv
import json
import re
from hashlib import sha256
from io import StringIO
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import to_canonical_graph
from rdflib.exceptions import ParserError
from rdflib.namespace import OWL, RDF, RDFS, SH, XSD
from rdflib.plugins.parsers.notation3 import BadSyntax

from app.adapters.ontology import OntologyAdapter

RECORD = URIRef("https://knowledge.example/imports/ImportedRecord")
MAX_ROWS = 10000


def key(value):
    stem = re.sub(r"[^A-Za-z0-9_]", "_", value.rsplit("/", 1)[-1].rsplit("#", 1)[-1])[:40]
    if not stem or not stem[0].isalpha():
        stem = "Field_" + stem
    return stem + "_" + sha256(value.encode()).hexdigest()[:8]


def text_decode(data):
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Save this file as UTF-8 and try again.")


def csv_data(data):
    text = text_decode(data)
    csv.field_size_limit(20 * 1024 * 1024)
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(StringIO(text, newline=""), dialect=dialect, strict=True)
    try:
        columns = next(reader, [])
        if not columns or any(not c.strip() for c in columns) or len(columns) != len(set(columns)):
            raise ValueError("CSV needs a header row with unique, nonempty column names.")
        if len(columns) > 100:
            raise ValueError("Use a CSV with at most 100 columns.")
        rows = []
        for cells in reader:
            if not cells or not any(cells):
                continue
            if len(cells) != len(columns):
                raise ValueError(
                    f"CSV record {len(rows) + 1} has a different number of values than the header."
                )
            rows.append(dict(zip(columns, cells)))
            if len(rows) > MAX_ROWS:
                raise ValueError("Split this CSV into files of at most 10,000 records.")
        if not rows:
            raise ValueError("This CSV has headers but no records. Add at least one data row.")
        return columns, rows
    except csv.Error:
        raise ValueError("This CSV has malformed quoting. Check the file and try again.")


def from_rows(columns, rows, kind="csv"):
    definitions = Graph()
    definitions.add((RECORD, RDF.type, OWL.Class))
    definitions.add((RECORD, RDFS.label, Literal("Imported record")))
    records = []
    properties = {}
    for column in columns:
        prop = URIRef("https://knowledge.example/imports/columns/" + key(column))
        properties[column] = str(prop)
        definitions.add((prop, RDF.type, OWL.DatatypeProperty))
        definitions.add((prop, RDFS.label, Literal(column)))
        definitions.add((prop, RDFS.domain, RECORD))
        definitions.add((prop, RDFS.range, XSD.string))
    for index, row in enumerate(rows):
        label = next((str(v) for k, v in row.items() if k.lower() in ("name", "title", "label") and v), None)
        label = label or next((str(v) for v in row.values() if v), f"Record {index + 1}")
        records.append(
            {
                "id": "row-" + str(index + 1),
                "class_iris": [str(RECORD)],
                "label": label[:200],
                "values": {
                    properties[c]: [{"value": str(row[c]), "datatype": str(XSD.string), "language": None}]
                    for c in columns
                },
                "source_row": index + 1,
                "text": "\n".join(f"{c}: {row[c]}" for c in columns),
            }
        )
    return {
        "kind": kind,
        "columns": columns,
        "sample_rows": rows[:5],
        "records": records,
        "relationships": [],
        "definitions": definitions.serialize(format="turtle"),
    }


def json_rows(data, records_path=""):
    try:
        value = json.loads(text_decode(data))
        for part in records_path.split(".") if records_path else []:
            value = value[part]
    except (ValueError, KeyError, TypeError):
        raise ValueError("Could not find a JSON record array at this records path.")
    if not isinstance(value, list) or not value or any(not isinstance(row, dict) or not row for row in value):
        raise ValueError("Use a JSON array of nonempty objects, or specify the path to that array.")
    columns = list(dict.fromkeys(c for row in value for c in row))
    if len(columns) > 100:
        raise ValueError("Use records with at most 100 fields.")
    rows = [
        {
            c: ""
            if row.get(c) is None
            else row[c]
            if isinstance(row[c], str)
            else json.dumps(row[c], ensure_ascii=False)
            for c in columns
        }
        for row in value
    ]
    return columns, rows


def turtle_data(data):
    text = text_decode(data)
    try:
        graph = to_canonical_graph(OntologyAdapter().parse(text))
    except (ParserError, BadSyntax, ValueError, TypeError):
        raise ValueError("This Turtle file could not be read. Check its syntax and try again.")
    if not len(graph):
        raise ValueError("This Turtle file contains no data or definitions.")
    if len(graph) > 50000:
        raise ValueError("Split this Turtle file into files of at most 50,000 statements.")
    definition_types = {
        OWL.Class,
        RDFS.Class,
        OWL.ObjectProperty,
        OWL.DatatypeProperty,
        OWL.Ontology,
        SH.NodeShape,
        SH.PropertyShape,
        RDF.Property,
    }
    definitions = Graph()
    definitions.bind("imported", "https://knowledge.example/imports/")
    defined = {s for s, _, o in graph.triples((None, RDF.type, None)) if o in definition_types}
    # SHACL property nodes may be blank nodes without an explicit type.
    pending = list(defined)
    while pending:
        for _, _, target in graph.triples((pending.pop(), None, None)):
            if isinstance(target, BNode) and target not in defined:
                defined.add(target)
                pending.append(target)
    for s in defined:
        for triple in graph.triples((s, None, None)):
            definitions.add(triple)
    subjects = {s for s in graph.subjects() if s not in defined}
    # Named object references are records too, even when described elsewhere.
    subjects |= {
        o
        for s, p, o in graph
        if s in subjects
        and p not in (RDF.type, RDFS.label, RDFS.comment)
        and isinstance(o, (URIRef, BNode))
        and o not in defined
    }
    if len(subjects) > MAX_ROWS:
        raise ValueError("Split this Turtle file into files of at most 10,000 records.")
    ids = {s: "rdf-" + sha256(str(s).encode()).hexdigest()[:24] for s in subjects}
    records, relationships = [], []
    inferred = []

    def infer(triple):
        if triple not in definitions:
            definitions.add(triple)
            inferred.append([str(term) for term in triple])

    property_kinds = {}
    for subject in sorted(subjects, key=str):
        if any(not isinstance(o, URIRef) for o in graph.objects(subject, RDF.type)):
            raise ValueError("Use a named concept identifier for each record type.")
        classes = sorted(str(o) for o in graph.objects(subject, RDF.type) if o not in definition_types)
        classes = classes or [str(RECORD)]
        for class_iri in classes:
            node = URIRef(class_iri)
            if not any(definitions.triples((node, RDF.type, None))):
                infer((node, RDF.type, OWL.Class))
        values = {}
        labels = []
        for predicate, value in sorted(
            graph.predicate_objects(subject), key=lambda pair: (str(pair[0]), str(pair[1]))
        ):
            if predicate == RDF.type:
                continue
            kind = "datatype" if isinstance(value, Literal) else "object"
            if predicate in property_kinds and property_kinds[predicate] != kind:
                raise ValueError(
                    "A Turtle property is used for both values and relationships. Separate those properties."
                )
            property_kinds[predicate] = kind
            declared = set(definitions.objects(predicate, RDF.type))
            wanted = OWL.DatatypeProperty if kind == "datatype" else OWL.ObjectProperty
            if (declared & {OWL.DatatypeProperty, OWL.ObjectProperty}) - {wanted}:
                raise ValueError("A Turtle property value disagrees with its declared kind.")
            infer((predicate, RDF.type, wanted))
            if kind == "datatype":
                term = {
                    "value": str(value),
                    "datatype": str(value.datatype) if value.datatype else None,
                    "language": value.language,
                }
                values.setdefault(str(predicate), []).append(term)
                labels.append(f"{predicate.rsplit('/', 1)[-1].rsplit('#', 1)[-1]}: {value}")
            elif value in ids:
                if not definitions.value(predicate, RDFS.range):
                    target_class = next(
                        (
                            c
                            for c in graph.objects(value, RDF.type)
                            if isinstance(c, URIRef) and c not in definition_types
                        ),
                        RECORD,
                    )
                    infer((predicate, RDFS.range, target_class))
                    if not any(definitions.triples((target_class, RDF.type, None))):
                        infer((target_class, RDF.type, OWL.Class))
                relationships.append({"source": ids[subject], "target": ids[value], "iri": str(predicate)})
                labels.append(f"{predicate.rsplit('/', 1)[-1].rsplit('#', 1)[-1]}: {value}")
        record_iri = str(subject) if isinstance(subject, URIRef) else "urn:knowledge:blank:" + str(subject)
        business_name = next(
            (
                value
                for predicate, value in graph.predicate_objects(subject)
                if isinstance(value, Literal)
                and str(predicate).rsplit("/", 1)[-1].rsplit("#", 1)[-1].lower()
                in ("name", "title", "identifier")
            ),
            None,
        )
        label = str(
            graph.value(subject, RDFS.label)
            or business_name
            or ("Unnamed record" if isinstance(subject, BNode) else record_iri.rsplit("/", 1)[-1])
        )
        records.append(
            {
                "id": ids[subject],
                "blank_node": isinstance(subject, BNode),
                "iri": record_iri,
                "class_iris": classes,
                "label": label[:200],
                "values": values,
                "source_subject": record_iri,
                "text": "\n".join([label, "Type: " + ", ".join(classes), *labels]),
            }
        )
    if not records and not len(definitions):
        raise ValueError("This Turtle file has no supported records or business definitions.")
    return {
        "kind": "turtle" if records else "definitions",
        "columns": [],
        "sample_rows": [],
        "records": records,
        "relationships": relationships,
        "definitions": definitions.serialize(format="turtle"),
        "inferred": inferred,
    }


def parse(name, data):
    extension = Path(name).suffix.lower()
    if extension == ".csv":
        return from_rows(*csv_data(data))
    if extension in (".ttl", ".turtle"):
        return turtle_data(data)
    if extension == ".json":
        columns, rows = json_rows(data)
        if len(rows) > MAX_ROWS:
            raise ValueError("Split this JSON into files of at most 10,000 records.")
        return from_rows(columns, rows, "json")
    return {"kind": "document", "records": [], "relationships": [], "columns": [], "sample_rows": []}


def preview(name, data):
    if not data or len(data) > 20 * 1024 * 1024:
        raise ValueError("Choose a nonempty file of at most 20 MB.")
    if Path(name).suffix.lower() not in (".csv", ".json", ".ttl", ".turtle", ".pdf", ".docx", ".txt", ".md"):
        raise ValueError("Use CSV, JSON records, Turtle, PDF, Word, text, or Markdown.")
    result = parse(name, data)
    graph = OntologyAdapter().parse(result["definitions"]) if result.get("definitions") else Graph()
    inspected = OntologyAdapter().inspect(graph)
    return {
        "name": Path(name).name,
        "kind": result["kind"],
        "record_count": len(result["records"]),
        "columns": result["columns"],
        "sample_rows": result["sample_rows"],
        "concept_count": len(inspected["classes"]),
        "relationship_count": len(result["relationships"]),
        "warnings": inspected["unsupported_constructs"],
        "sha256": sha256(data).hexdigest(),
    }
