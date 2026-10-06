# Adapter contracts

All adapters receive revision-scoped inputs. Product, revision, document/chunk, processing, model, ontology, mapping, and graph build identities are retained in derived artifacts and release manifests.

| Adapter | Current implementation | Contract and replacement seam |
|---|---|---|
| ObjectStore | MinIO Python SDK, immutable SHA-256 object keys | `put(bytes, content_type) -> ArtifactRef`; `get(ArtifactRef) -> bytes`; `verify(key, sha256)` reads and validates integrity. Replace with S3-compatible storage without changing business services. |
| OntologyAdapter | RDFLib, pySHACL, canonical Turtle files | `parse(turtle) -> Graph`, `inspect(Graph) -> definitions`, `validate(ontology, shapes, instances) -> findings`. A future triplestore implements persistence/querying behind a separate store interface; pgvector is not RDF storage. |
| EmbeddingProvider | Pinned local SentenceTransformer | `embed(list[str], ModelRef) -> list[list[float]]`. Exactly 384 finite nonzero values enter this index. Documents and queries use the identical name and resolved model revision. A different dimension requires a separate index/migration and an explicit configuration change. |
| GraphAdapter | FalkorDB via Redis protocol | `build(GraphBuild)`, `verify(GraphBuild)`, `search(build, query, entity_type, limit)`, `neighbors(build, entity_id, limit)`. Build keys scope database, product, revision, and immutable build UUID. Values are bound through CYPHER parameters; label/type identifiers are validated; integer bounds are clamped. |
| JobRunner | Separate PostgreSQL worker | `run_once(worker_id) -> bool`. Jobs have unique input fingerprints, stage state, leases, attempts, and errors. Claimed rows are locked through stage side effects; retries reuse completed unchanged artifacts. A future queue runner must preserve these guarantees. |

## Supported semantics

Classes, subclass links, object and datatype properties, domains/ranges, labels, descriptions, namespaces, and SHACL minCount/maxCount/datatype constraints are supported. Rule violations identify the instance and property. Imports retain unsupported constructs with explicit warnings; unsupported rules do not earn passing conformance. Unrestricted OWL reasoning and a remote SPARQL endpoint are not implemented.

Guided edits create stable IRIs automatically and prepare mappings. Advanced editors can inspect RDF and modify validated mappings. Existing definition collisions and namespace conflicts are rejected. Impact previews identify affected facts and required rebuild/check/review work. Published graph data is preserved.

## Fixture extraction

The documented complaint fixture identifies `Complaint C-… submitted by Customer A-…`, linking both facts to their exact source chunks. Other documents produce evidence-backed knowledge items using the first mapped concept. This deterministic demo is not arbitrary enterprise entity extraction. Every node and relationship is labeled with fixture provenance; stronger extraction providers can replace this stage while preserving evidence and build identities.

## Consistency and extensions

Evaluation fingerprints capture the current versioned inputs. Submitted revisions changed by authors yield superseded reviews; stale evidence cannot authorize publication. Graph readiness and object integrity are checked before PostgreSQL atomically activates the prepared manifest. A failed preparation leaves the prior active manifest intact. Active/pinned consumer policies resolve releases without mixing artifacts.

Real external connectors, production identity, remote RDF stores, arbitrary extraction, and optional LLM answer generation are extension work. External source locations in this MVP are registration metadata; only uploads and labeled fixture synchronization produce stored documents.
