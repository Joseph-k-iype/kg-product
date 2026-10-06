Use **PostgreSQL with pgvector, MinIO, an RDF ontology layer, and FalkorDB**. The UI should present these as one knowledge product while making provenance and publication state clear.

One architectural decision remains: **pgvector stores embeddings; it does not provide RDF storage or SPARQL queries.** For the MVP, store versioned RDF files in MinIO, keep their metadata in PostgreSQL, and use an RDF library for validation and inspection. Add a dedicated RDF triplestore later if server-side SPARQL becomes necessary.

# Knowledge Product Manager — Revised Architecture, UI, and Workflows

## 1. Problem statement

Enterprise knowledge is spread across documents, operational systems, policies, support records, and application inventories. Turning this information into reliable knowledge for AI requires several connected representations:

- Original documents and extracted content.
- Shared concepts and semantic definitions.
- Instances and their relationships.
- Embeddings for semantic retrieval.
- Ownership, provenance, evaluations, and approvals.
- Published releases consumed by applications.

These representations often live in separate systems. Teams lack a coherent way to manage their lifecycle, assess readiness, review changes, and trace answers to evidence.

Build a Knowledge Product Manager that lets teams create, maintain, evaluate, approve, publish, and consume enterprise knowledge products.

The central user experience should answer:

> What knowledge does this product contain, where did it come from, what does it mean, can we trust it, and who depends on it?

## 2. Storage architecture

| Component | Responsibility |
|---|---|
| PostgreSQL | Products, revisions, source metadata, document/chunk records, workflows, quality results, permissions metadata, consumers, activity |
| pgvector | Chunk embeddings and semantic similarity search within PostgreSQL |
| MinIO | Original documents, extracted-text artifacts, versioned RDF ontology files, release manifests |
| RDF ontology layer | Semantic definitions, ontology parsing, validation, serialization, and inspection |
| FalkorDB | Labeled property graph containing knowledge instances and their relationships |

### Document handling

Store original PDFs, Word files, text files, and other uploaded objects in MinIO.

Store document metadata, extracted text or chunk text, provenance pointers, and processing state in PostgreSQL. Store embeddings on chunk records through pgvector.

A document record must connect:

`Original object → Extracted content → Chunks → Embeddings → Graph instances`

Each derived representation carries a document ID, product ID, revision ID, and processing version.

### RDF ontology versus instance graph

Keep their responsibilities explicit:

- **RDF ontology:** Defines classes, properties, meaning, constraints, and vocabulary mappings.
- **FalkorDB graph:** Contains actual entities and relationships extracted or authored for a product.

Example:

- RDF defines `Complaint`, `Customer`, and `submittedBy`.
- FalkorDB contains Complaint C-1042, Customer A-203, and their relationship.
- A mapping specifies how the RDF vocabulary corresponds to FalkorDB labels and relationship types.

Do not assume that RDF properties map perfectly to property-graph labels. Maintain an explicit, versioned mapping.

### MVP RDF approach

- Use RDF, RDFS, and a constrained OWL vocabulary for definitions.
- Use SHACL for supported validation constraints.
- Store ontology artifacts as versioned Turtle files in MinIO.
- Store artifact references, hashes, versions, and mappings in PostgreSQL.
- Parse and validate through an RDF library.
- Persist user edits back to the canonical RDF artifact.
- Keep an adapter boundary for a future RDF triplestore.

Do not present unrestricted OWL reasoning or a remote SPARQL endpoint as implemented capabilities.

## 3. Product and revision model

A knowledge product includes:

- Business purpose, domain, owner, and tags.
- Sources and document scope.
- RDF ontology version.
- Ontology-to-FalkorDB mapping version.
- Processing configuration.
- Document/chunk snapshot.
- Embedding model and index configuration.
- Instance graph build identifier.
- Retrieval configuration.
- Quality gates and evaluation evidence.
- Review decisions.
- Published releases and consumers.

A release manifest records the exact versions of these components.

Published consumers must use a consistent release rather than a mixture of the newest ontology, older graph, and newer embeddings.

## 4. Primary navigation

Use these destinations:

1. Overview
2. Knowledge Products
3. Sources
4. Ontology Studio
5. Knowledge Explorer
6. Knowledge Health
7. Reviews
8. Retrieval Playground
9. Lineage
10. Consumers

Keep infrastructure details in a secondary operational view. Product owners should see “Documents ready” or “Graph build failed” before implementation details such as bucket names or graph keys.

## 5. Overall UI direction

Use a clean enterprise application shell:

- Persistent sidebar.
- Workspace and product context in the header.
- Breadcrumbs for nested views.
- Clear titles and contextual primary actions.
- Tables for catalogs, sources, reviews, and consumers.
- Split-pane editors for semantic work.
- Graph views supported by searchable lists.
- Drawers for quick inspection.
- Full pages for complex editing and review.

Use color consistently:

- Neutral: draft or inactive.
- Blue: processing or informational.
- Green: ready or passed.
- Amber: needs attention.
- Red: failed or blocked.

Always pair color with a text label.

The interface must distinguish four separate dimensions:

1. Product lifecycle.
2. Processing readiness.
3. Knowledge quality.
4. Review/publication state.

A single “Healthy” badge cannot communicate all four.

## 6. Dashboard workflow

### User intent

Understand what needs attention and where to act.

### Screen composition

- Summary: active products, pending reviews, blocked releases, overdue sources.
- Attention queue: issue, product, owner, severity, corrective action.
- Product readiness table.
- Recent publications and activity.

### Flow

1. Open Overview.
2. Select an issue.
3. Navigate directly to its affected record.
4. Resolve the issue.
5. Return to an updated dashboard.

Examples of actionable issues:

- “HR Policies has an overdue source.”
- “Payments revision 3 has unmapped ontology classes.”
- “Customer Complaints has 18 chunks awaiting embeddings.”
- “Application Estate is ready for review.”

## 7. Knowledge product catalog and creation

### Catalog

Show:

- Product name and purpose.
- Domain and owner.
- Active release.
- Draft revision state.
- Quality status.
- Source freshness.
- Consumer count.

Support search, combined filters, sorting, and bookmarkable URLs.

### Creation flow

Use five steps:

1. **Purpose:** Name, description, domain, owner.
2. **Sources:** Select sources or upload documents.
3. **Semantics:** Choose an ontology template, import RDF, or start an empty ontology.
4. **Readiness:** Set quality gates and retrieval defaults.
5. **Review configuration:** Summarize and create the draft.

Allow an incomplete draft. Show a readiness checklist rather than forcing users to complete every configuration immediately.

After creation, open the product workspace with clear next actions:

- Add documents.
- Define ontology.
- Configure mappings.
- Process knowledge.
- Evaluate readiness.

## 8. Product workspace

Use a summary page with contextual tabs:

- Overview
- Sources & Documents
- Ontology
- Knowledge Graph
- Processing
- Health
- Reviews
- Retrieval
- Lineage
- Consumers
- Releases & Activity

The overview shows:

- Purpose and ownership.
- Current published release.
- Current draft.
- Readiness checklist.
- Blocking issues.
- Recent changes.

Editing a published product creates or opens its draft revision. Existing consumers continue using the published release.

## 9. Source and document workflow

### Source registration

1. Choose source type.
2. Enter name, owner, location, and freshness target.
3. Associate products.
4. Save.
5. Upload local documents or run a fixture-backed demo synchronization.

### Document upload

1. Select a product draft.
2. Upload a supported file.
3. Store the original object in MinIO.
4. Record metadata and processing state in PostgreSQL.
5. Queue extraction.
6. Show stage-by-stage progress.

### Document detail

Use a split view:

- Left: original document or extracted-text preview.
- Right: metadata, provenance, processing stages, chunks, linked entities, and issues.

Processing stages:

`Uploaded → Extracted → Chunked → Embedded → Graph built → Validated`

Show partial failures at the stage where they occur. Provide retry for failed work without duplicating successful artifacts.

Clearly distinguish registered external sources from actual connected sources.

## 10. Ontology Studio workflow

### User intent

Define what the knowledge means and how it should be represented.

### Screen layout

Use three panes:

- **Left:** Searchable classes, properties, namespaces, and shapes.
- **Center:** Definition editor or schema graph.
- **Right:** Details, validation findings, mappings, and usage impact.

Provide views for:

- Classes.
- Object properties.
- Datatype properties.
- SHACL shapes.
- Namespaces.
- FalkorDB mappings.
- RDF source.

### Create a class

1. Choose “Add class.”
2. Enter label and stable IRI.
3. Add description.
4. Select an optional parent class.
5. Save to the draft ontology.
6. Display the class in list and graph views.

### Create a property

1. Choose object or datatype property.
2. Enter label and IRI.
3. Select domain.
4. Select range or datatype.
5. Add description.
6. Save.

### Add a validation shape

1. Select the target class.
2. Choose a property.
3. Define supported constraints such as required value, datatype, or cardinality.
4. Preview the constraint in plain language.
5. Validate sample instances.
6. Save.

Example:

> Every Complaint must have exactly one complaint identifier.

### Import RDF

1. Upload Turtle.
2. Parse and validate.
3. Preview classes, properties, namespaces, and conflicts.
4. Show unsupported constructs explicitly.
5. Choose merge or replacement.
6. Save as a draft ontology version.

Replacement requires an impact preview before applying.

### Map RDF to FalkorDB

1. Select an RDF class.
2. Assign its graph label.
3. Map datatype properties to graph properties.
4. Map object properties to relationship types.
5. Validate coverage and conflicts.
6. Save the mapping version.

### Change impact

Before removing or changing a used definition, show:

- Affected mappings.
- Existing instance counts.
- Validation shapes.
- Evaluations and releases that reference it.
- Required rebuild steps.

Never silently delete affected instance data.

## 11. Knowledge Explorer workflow

Keep this separate from Ontology Studio.

Ontology Studio defines concepts. Knowledge Explorer inspects actual instances.

### Screen layout

- Product and revision selector.
- Search and entity-type filters.
- Graph canvas.
- Searchable results table.
- Entity details drawer.

### Flow

1. Search for an entity.
2. Open its attributes.
3. Expand neighboring relationships.
4. Inspect supporting documents and excerpts.
5. Navigate to the original source.
6. Flag an incorrect entity or relationship for review.

Default to a bounded neighborhood rather than loading the entire graph.

An instance or relationship must expose its evidence and extraction version where available. User-authored facts must show their authoring provenance.

## 12. Processing and readiness workflow

A dedicated Processing tab shows the readiness of each representation:

| Representation | Example state |
|---|---|
| Original objects | 12 of 12 stored |
| Extracted documents | 11 of 12 ready |
| Chunks | 240 generated |
| Embeddings | 228 of 240 ready |
| Ontology mapping | 2 classes unmapped |
| Instance graph | Build awaiting valid mapping |

### Flow

1. Review required work.
2. Run processing.
3. Monitor stage progress.
4. Inspect failures.
5. Retry failed stages.
6. Run evaluations when inputs are ready.

Use a persisted job model with attempt history and idempotent stage execution.

The MVP may use a local worker process and PostgreSQL-backed jobs. Keep worker execution behind an interface for later queue infrastructure.

## 13. Knowledge health workflow

Show separate dimensions:

- Source freshness.
- Extraction coverage.
- Required metadata completeness.
- Embedding coverage.
- Ontology mapping coverage.
- SHACL conformance.
- Evidence/citation coverage.

Do not collapse these into an unexplained composite score.

### Evaluation flow

1. Select a draft revision.
2. Capture its input versions.
3. Run checks.
4. Store results and findings.
5. Show measured values against configured thresholds.
6. Link each finding to the affected record.
7. Compare with previous runs.

Missing inputs produce an insufficient-data result, not a passing score.

Changes to evaluated inputs make the previous evaluation stale.

## 14. Review and publication workflow

### Review submission

1. Complete required processing.
2. Run current evaluations.
3. Resolve blocking failures.
4. Enter a change summary.
5. Submit the revision.

### Reviewer workspace

Use a change-oriented layout:

- Summary and requester.
- Before/after metadata.
- Ontology additions, removals, and changes.
- Mapping changes.
- Document changes.
- Quality evidence.
- Consumer impact.

### Decision

- Approve.
- Reject with reason.

Changing a submitted revision supersedes its review request.

### Publication

1. Verify approval and current evaluation evidence.
2. Build a release manifest.
3. Confirm all referenced artifacts are ready.
4. Activate the release in PostgreSQL.
5. Record publication activity.

PostgreSQL, MinIO, and FalkorDB cannot share one database transaction. Prepare and verify immutable artifacts first, then atomically activate their manifest. Failed preparation must leave the previous release active.

## 15. Retrieval Playground workflow

### Screen layout

- Product and release selector.
- Query input.
- Retrieval mode.
- Result limit.
- Results with evidence.
- Expandable diagnostics.

### Retrieval modes

- **Vector:** Search pgvector embeddings.
- **Graph:** Resolve supported entity queries and bounded relationships in FalkorDB.
- **Hybrid:** Retrieve semantic matches and expand relevant graph context.

Implement vector mode first. Enable graph and hybrid only when their adapters work.

### Flow

1. Select a published release or labeled draft preview.
2. Enter a query.
3. Run retrieval.
4. Inspect ranked chunks and graph context.
5. Open citations.
6. Trace the result to its source.
7. Optionally save the query as an evaluation case.

Use the same embedding model for documents and queries. Store model identity and vector dimension. Prevent incompatible vectors from entering the same search path.

Choose an explicit local embedding provider or a configured external provider. If unavailable, display an actionable error; do not silently substitute lexical search while calling it vector retrieval.

LLM answer generation remains optional. The MVP can deliver useful ranked evidence without generated answers.

## 16. Lineage and consumers

### Lineage

Show:

`Source → MinIO document → Extracted content → Chunks → Embeddings / Graph instances → Product release → Consumer`

Also show ontology and mapping versions used by graph builds.

Select a node to inspect its version, provenance, processing state, and dependencies.

Provide a table alternative to the visual graph.

### Consumers

Register:

- Agent.
- Copilot.
- API application.
- Dashboard.

Associate products and choose:

- Track the active release.
- Pin to a specific release.

Display dependencies and clearly labeled demo usage figures.

## 17. Implementation sequence

### Phase 1: Foundation and product management

- Local PostgreSQL with pgvector, MinIO, and FalkorDB.
- Application/API/worker setup.
- Migrations and seed fixtures.
- Product catalog, creation, editing, and revision model.

### Phase 2: Document lifecycle

- Upload to MinIO.
- Document records and provenance.
- Extraction and chunking.
- Processing jobs, retries, and stage visibility.

### Phase 3: RDF ontology and mappings

- RDF artifact versioning.
- Class/property editor.
- RDF import/export.
- Supported SHACL validation.
- Ontology-to-FalkorDB mapping editor.

### Phase 4: Embeddings and instance graph

- Embedding provider and pgvector search.
- Fixture-backed entity/relationship generation.
- FalkorDB graph builds.
- Knowledge Explorer.

### Phase 5: Governance

- Quality checks.
- Review queue and decisions.
- Change invalidation.
- Release preparation and activation.

### Phase 6: Consumption and UI completion

- Retrieval Playground.
- Lineage.
- Consumer associations.
- Dashboard attention flows.
- Responsive and accessibility checks.

## 18. Required acceptance tests

Verify:

- Product and revision persistence.
- Original document storage and retrieval through MinIO.
- Failed processing and safe retries.
- Valid RDF import/export round trips.
- Stable IRIs and namespace handling.
- Invalid ontology mappings being rejected.
- SHACL findings linking to affected instances.
- Embedding dimension/model compatibility.
- Product and revision isolation in vector and graph queries.
- Citations pointing to correct source evidence.
- Ontology changes invalidating dependent builds/evaluations.
- Stale approvals being blocked.
- Failed release preparation preserving the active release.
- Consumer pinning and lineage accuracy.
- Full browser journey from product creation through retrieval.

## 19. Codex delivery requirements

Deliver a working application with:

- Modular source code.
- Local service orchestration.
- Database migrations.
- Synthetic demo data and document fixtures.
- Tests and verified results.
- Setup, reset, and troubleshooting instructions.
- Adapter documentation.
- A running local preview.

Treat every primary action as a real persisted workflow. Clearly label fixture-backed processing, demo identities, and simulated usage.
## 20. Agreed implementation design

### Application structure

Use a React and TypeScript frontend with Vite, a Python FastAPI API, and a separate Python worker. Docker Compose orchestrates PostgreSQL with pgvector, MinIO, FalkorDB, API, and worker. The frontend runs locally for development. Keep backend modules organized around products, sources/documents, ontology/mappings, processing, evaluations, reviews/releases, retrieval, and consumers/lineage. Use SQLAlchemy and Alembic for database access and migrations. Use explicit adapters for object storage, ontology operations, embeddings, graph operations, and job execution.

The MVP is a local, single-workspace application with synthetic identities. Identity selection supports author and reviewer journeys and records attribution; it is not production authentication or authorization. The UI clearly identifies this limitation. Production identity integration is outside this delivery.

### Persistence and consistency

Products have immutable revision identifiers and a mutable draft until submission. Every mutation increments the revision input generation and records an activity event. Published revisions are immutable; editing opens a new draft. Submitted revision changes supersede the review and invalidate its decisions.

Documents, chunks, ontology artifacts, mappings, builds, evaluations, and reviews reference a product and revision. Content-derived artifacts additionally record input generation, processing version, and relevant model identity. Release manifests pin document/chunk snapshots, ontology hash/version, mapping version, graph build, embedding model/dimension, retrieval configuration, evaluation evidence, and review decisions.

Prepare immutable artifacts before activating a release. Verify storage objects, graph readiness, model compatibility, current passing gates, and approval against the captured generation. Atomically activate the manifest and record publication in PostgreSQL with a generation check. Failed preparation preserves the active release. Consumers either follow that active manifest or reference a specific immutable manifest.

### Documents and processing

Support UTF-8 text, PDF, and DOCX uploads. Store originals under immutable MinIO object keys with hashes and content types. Extract text using format-specific libraries, retain extracted artifacts, and create deterministic chunks with source offsets. Textless or unsupported files produce actionable stage errors.

PostgreSQL jobs record stage, inputs, state, attempts, timestamps, and errors. Workers claim jobs with row locking; attempt leases allow recovery after worker interruption. Artifact uniqueness and input fingerprints make retries idempotent. Retry resumes the failed stage and dependent work, preserving completed artifacts for unchanged inputs.

Fixture-backed entity extraction uses documented synthetic document fixtures and explicit deterministic rules. Mark generated graph entities and relationships with fixture provenance, source chunk references, extraction version, and build identifier. External source registration records location and freshness targets; only local uploads and fixture synchronization are implemented connections.

### Ontology and graph semantics

RDFLib parses and serializes canonical Turtle; pySHACL validates the supported shapes. Support classes, subclass relationships, object/datatype properties, domains, ranges, namespaces, descriptions, and SHACL minCount, maxCount, and datatype constraints. Reject unsupported edits and report imported unsupported constructs explicitly. No unrestricted OWL reasoning or remote SPARQL endpoint is exposed.

Ontology changes create new immutable artifacts and metadata references. Stable IRIs identify definitions independently of labels. Replacement and destructive definition changes require an impact preview. Validate mappings for existing IRIs, compatible property kinds, unique/conflict-free labels and properties, and supported relationship domain/range targets. A graph build pins its ontology and mapping versions. Definition edits invalidate dependent draft builds and evaluations without deleting published graph data.

FalkorDB stores bounded, revision/build-scoped instance graphs. All queries constrain product, revision, and build; adapters use parameterized queries and validate identifiers. Explorer exposes searchable instances, bounded neighborhoods, supporting excerpts, and review flags. Graph and hybrid retrieval become enabled only after their adapters pass integration tests.

### Embeddings and retrieval

Default to a local sentence-transformers provider using all-MiniLM-L6-v2, producing 384-dimensional vectors. Pin the resolved model revision in the embedding configuration and record it with each build. Document and query embeddings use the identical configured model revision. Initial model download needs network access; missing model files or provider failures return actionable errors and never substitute lexical search under a vector label.

pgvector search filters the selected release's exact chunk snapshot and compatible model/dimension before ranking. Draft preview explicitly identifies its draft revision and input generation. Retrieval returns ranked evidence and correct source citations; generated answers are outside the MVP. Graph mode supports entity lookup and bounded relationships; hybrid mode expands graph context from vector-result evidence. Diagnostics expose model, release, timing, and retrieval inputs.

### Evaluations and governance

Persist each evaluation run's input fingerprint, metric values, thresholds, and affected-record findings. Evaluate freshness, extraction, metadata, embedding coverage, mapping coverage, supported SHACL conformance, and citation coverage separately. Missing inputs yield insufficient-data results. Changed fingerprints yield stale evidence.

Submission requires ready inputs and current passing required gates. Reviews show version changes and consumer impact, and capture approve/reject decisions with reasons and synthetic reviewer identity. Publication requires a current approval and current gate evidence. Concurrent edits or superseded reviews cannot authorize activation.

### Interface and accessibility

Implement all ten primary destinations and product workspace tabs described above. Use a consistent enterprise shell, contextual product/revision selectors, bookmarkable catalog filters, tables, split editors, evidence drawers, and bounded graph canvases with equivalent list/table access. Each primary action performs an API-backed persisted operation and reports pending, success, empty, and error states.

Keep lifecycle, processing, quality, and publication states separate. Status labels accompany colors. Forms use explicit labels and actionable validation; navigation and dialogs support keyboard operation and focus management. Responsive layouts retain access to editors and tables at narrow widths. Infrastructure details belong in a secondary operational view.

### Verification and delivery

Use pytest for domain and adapter tests, integration tests against the Compose services, and Playwright for browser acceptance. Cover every acceptance case in section 18, including concurrency/staleness, release preparation failures, revision isolation, RDF round trips, retries, and pinned consumers. Separate fast tests from infrastructure/model-dependent checks and document exact commands and any execution limitations.

Deliver migrations, deterministic seed and reset tooling, synthetic document fixtures, setup/reset/troubleshooting instructions, adapter contracts, and a running local preview. Report only tests actually executed as passing. Local services and model availability must be verified before claiming the full end-to-end system works.

### Implementation boundaries

This specification includes all six phases in section 17. Deliver incrementally in that order while preserving the final end-to-end scope. Dedicated RDF triplestore, production authentication, real external source connectors, unrestricted ontology reasoning, and LLM answer generation remain future adapter extensions. Simulated usage is explicitly labeled; real product and consumer configuration is persisted.

## 21. Business-user simplicity — user correction during implementation

Primary workflows must be usable without understanding graphs, Turtle, RDF, embeddings, or infrastructure. Present ontology work as Concepts & Rules, graph exploration as Explore Knowledge, mappings as advanced representation settings, and processing as Prepare Knowledge. Use business forms and plain-language constraint previews, evidence-first searchable lists, guided next actions, and a simple readiness checklist. Keep technical RDF source, graph queries, storage identifiers, and mapping mechanics in explicit Advanced views. The underlying storage and version/provenance guarantees remain required. Standard navigation labels may use these business-friendly equivalents while maintaining all specified destinations.

## 22. Additional design direction

Use a modern grid of flat business-oriented blocks, clear tables, and generous spacing. WeKnora (https://github.com/Tencent/WeKnora) informs document-first onboarding, visible preparation timelines, source-linked retrieval evidence, and modular adapters. This is inspiration rather than a platform migration; retain the approved storage and release/governance architecture.
