# Knowledge Product Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Deliver the complete local Knowledge Product Manager with persisted document, semantic, governance, and retrieval workflows.

**Architecture:** React/TypeScript frontend communicates with FastAPI. PostgreSQL records revisions and workflows; MinIO holds immutable artifacts; FalkorDB holds scoped instance builds. A separate worker executes leased PostgreSQL jobs through explicit adapters.

**Tech Stack:** Vite, React, TypeScript, FastAPI, SQLAlchemy, Alembic, PostgreSQL/pgvector, MinIO, FalkorDB, RDFLib, pySHACL, sentence-transformers, pytest, Playwright.

**Spec:** ../specs/2026-10-06-knowledge-product-manager-design.md

## Global Constraints

- Use a React and TypeScript frontend with Vite, a Python FastAPI API, and a separate Python worker.
- Default to a local sentence-transformers provider using all-MiniLM-L6-v2, producing 384-dimensional vectors.
- Document and query embeddings use the identical configured model revision.
- No unrestricted OWL reasoning or remote SPARQL endpoint is exposed.
- Published revisions are immutable; editing opens a new draft.
- Failed preparation preserves the active release.
- Treat every primary action as a real persisted workflow.
- Clearly label fixture-backed processing, demo identities, and simulated usage.
- Follow the six phases without dropping final scope. Use 12ui draft, branch, and target comparison for the frontend; read CLI help before invoking commands.

## Review Focus

- Concurrent author edits: optimistic generation checks reject lost updates (task 1).
- Malformed, empty, or textless uploads: preserve originals and report stage-specific failures (task 2).
- Namespace and IRI collisions: reject ambiguous merges and retain stable identities (task 3).
- Worker death after artifact creation: lease recovery reuses artifacts without duplication (task 2).
- Dependency failure during activation: leave the previous manifest and pinned consumers intact (task 6).

## Shared contracts and file structure

All backend paths are under `backend/`; Python package is `app`. Each feature has `models.py`, `schemas.py`, `service.py`, and `routes.py` under `app/features/<feature>/`. SQLAlchemy session is injected; API transactions end at request boundaries. UUID IDs and timezone-aware UTC timestamps are used throughout.

`app/domain/contracts.py` defines immutable DTOs: RevisionRef(product_id: UUID, revision_id: UUID, generation: int), ArtifactRef(key: str, sha256: str, version: str), ModelRef(name: str, revision: str, dimension: int), Evidence(chunk_id: UUID, document_id: UUID, start: int, end: int, text: str), and RetrievalHit(evidence: Evidence, score: float). Feature-specific DTOs live in the producing feature's schemas module.

`app/adapters/` contains storage.py, ontology.py, embeddings.py, graph.py, and jobs.py. Services consume injected adapter protocols; production implementations and test doubles share those contracts. `app/main.py`, `app/config.py`, and `app/db.py` own startup, environment, and persistence. `alembic/versions/` holds ordered migrations. `tests/unit/`, `tests/integration/`, and `tests/acceptance/` mirror features.

Frontend paths are `frontend/src/`. `api/client.ts` owns typed API requests and errors. `components/` owns shell, status labels, tables, dialogs, and drawers. `features/<feature>/` owns routes, forms, and query state. `tests/e2e/` holds browser acceptance tests. Generated 12ui assets and approved screenshots live in `design/`; retained exports supply the implementation baseline.

Root files: `compose.yaml`, `.env.example`, `Makefile`, `README.md`, `scripts/seed.py`, `scripts/reset.py`, `fixtures/documents/`, and `docs/adapters.md`. Reset targets only this application's database, bucket, and graph namespace.

## Execution conventions

For each task write the named assertions first, run its tests to observe failure, implement the contracts, then rerun to PASS and commit the task's files. Run backend tests from `backend` with `.venv/bin/python -m pytest`. API endpoints use `/api`; JSON errors contain code, message, and affected IDs. List endpoints are paginated. Mutations supply expected generation and produce HTTP 409 on conflicting generations. Preserve meaningful infrastructure errors.

---

### Task 1: Foundation and revision persistence

**Files:** Create `app/domain/contracts.py; app/config.py; app/db.py; app/main.py; app/features/products/{models,schemas,service,routes}.py; alembic/versions/001_foundation.py; pyproject.toml; Dockerfile; compose.yaml; .env.example; Makefile`. Test `tests/integration/test_products.py`. Paths follow the backend/frontend roots above; braces enumerate individual modules.

**Interfaces:** Produces create_product(session, input: ProductCreate) -> ProductDetail; open_draft(session, product_id: UUID) -> RevisionRef; update_draft(session, ref: RevisionRef, input: ProductUpdate) -> ProductDetail. ProductDetail includes owner, purpose, domain, tags, active release, draft state, and readiness. GET/POST /products, GET/PATCH /products/{id}, POST /products/{id}/draft; GET /health.

- [x] **Step 1: Write failing tests in `tests/integration/test_products.py` with these assertions.**

```python
assert create_then_reload.name == "Customer Complaints"
assert published_edit.revision_id != published.revision_id
assert stale_update.status_code == 409
assert catalog_combined_filters.total == 1
assert health.probes == {"postgres": "ready", "minio": "ready", "falkordb": "ready"}
```

- [x] **Step 2: Run `.venv/bin/python -m pytest tests/integration/test_products.py -v`.** Expect the named tests to fail because the behavior is absent; infrastructure setup failures do not count as a meaningful red test.
- [x] **Step 3: Implement the interfaces in the listed files.** Create service configuration, Compose health checks, migrations with vector extension, revisions and activity records. Configure catalog pagination/search/filter/sort. Scaffold API and integration fixtures; persist incomplete drafts. Seed synthetic identities and initial product fixtures.
- [x] **Step 4: Run `.venv/bin/python -m pytest tests/integration/test_products.py -v`.** Expect all task assertions to pass; also run preceding task tests when their contracts change.
- [x] **Step 5: Review the diff and commit only this task's files.** Use commit message `feat: foundation and revision persistence`. Record executed checks and any blockers before moving forward.

### Task 2: Document storage, provenance, and recoverable jobs

**Files:** Create `app/features/sources/{models,schemas,service,routes}.py; app/features/documents/{models,schemas,service,routes}.py; app/features/processing/{models,schemas,service,routes}.py; app/adapters/storage.py; app/adapters/jobs.py; app/worker.py; alembic/versions/002_documents_jobs.py; fixtures/documents/complaints.txt; fixtures/documents/policy.pdf; fixtures/documents/estate.docx`. Test `tests/integration/test_documents.py`. Paths follow the backend/frontend roots above; braces enumerate individual modules.

**Interfaces:** Consumes RevisionRef. Produces upload_document(session, ref: RevisionRef, file: UploadInput) -> DocumentDetail; enqueue_stage(session, ref: RevisionRef, document_id: UUID, stage: str) -> JobDetail; run_once(worker_id: str) -> bool. ObjectStore.put(data: bytes, content_type: str) -> ArtifactRef; ObjectStore.get(ref: ArtifactRef) -> bytes. GET/POST /sources; POST /sources/{id}/sync-fixture; POST /products/{id}/documents; GET /documents/{id}; GET /documents/{id}/original; POST /jobs/{id}/retry; GET /products/{id}/processing.

- [x] **Step 1: Write failing tests in `tests/integration/test_documents.py` with these assertions.**

```python
assert downloaded_bytes == uploaded_bytes
assert chunk.text == extracted_text[chunk.start:chunk.end]
assert retry.chunk_count == first.chunk_count
assert recovered.attempts == 2
assert textless_document.failed_stage == "extracted"
assert empty_upload.status_code == 422
assert external_source.connection_state == "registered"
```

- [x] **Step 2: Run `.venv/bin/python -m pytest tests/integration/test_documents.py -v`.** Expect the named tests to fail because the behavior is absent; infrastructure setup failures do not count as a meaningful red test.
- [x] **Step 3: Implement the interfaces in the listed files.** Implement immutable MinIO uploads, PDF/DOCX/text extraction and deterministic chunks. Persist stage attempts, leased row-lock claims, input fingerprints and artifact uniqueness. Simulate an interrupted worker in tests. Add source freshness and product associations. Record artifact/document/revision/processing provenance throughout.
- [x] **Step 4: Run `.venv/bin/python -m pytest tests/integration/test_documents.py -v`.** Expect all task assertions to pass; also run preceding task tests when their contracts change.
- [x] **Step 5: Review the diff and commit only this task's files.** Use commit message `feat: document storage, provenance, and recoverable jobs`. Record executed checks and any blockers before moving forward.

### Task 3: Versioned RDF ontology, shapes, and explicit mappings

**Files:** Create `app/features/ontology/{models,schemas,service,routes}.py; app/adapters/ontology.py; alembic/versions/003_ontology.py; fixtures/ontology/complaints.ttl; fixtures/ontology/complaints-shapes.ttl`. Test `tests/integration/test_ontology.py`. Paths follow the backend/frontend roots above; braces enumerate individual modules.

**Interfaces:** Consumes RevisionRef and ObjectStore. Produces save_ontology(session, ref: RevisionRef, edit: OntologyEdit) -> OntologyVersion; import_ontology(session, ref: RevisionRef, turtle: str, mode: str, impact_token: str | None) -> OntologyVersion; save_mapping(session, ref: RevisionRef, input: MappingInput) -> MappingVersion; inspect_impact(session, ref: RevisionRef, iri: str) -> ImpactDetail. OntologyAdapter.parse(turtle: str) -> OntologyDocument; validate(ontology: str, shapes: str, instances: str) -> list[Finding]. GET/PATCH /products/{id}/ontology; POST /ontology/import; GET /ontology/export; POST /ontology/impact; PUT /ontology/mapping, scoped by product revision.

- [x] **Step 1: Write failing tests in `tests/integration/test_ontology.py` with these assertions.**

```python
assert graph_isomorphic(imported, exported)
assert renamed.iri == original.iri
assert duplicate_namespace.status_code == 422
assert invalid_mapping.status_code == 422
assert missing_identifier.findings[0].entity_id == complaint_id
assert replacement_without_impact.status_code == 409
assert unsupported_constructs != []
```

- [x] **Step 2: Run `.venv/bin/python -m pytest tests/integration/test_ontology.py -v`.** Expect the named tests to fail because the behavior is absent; infrastructure setup failures do not count as a meaningful red test.
- [x] **Step 3: Implement the interfaces in the listed files.** Use RDFLib and pySHACL; implement class, property, namespaces, supported shape edits and canonical serialization. Store hash/version/object references. Preview merge conflicts and replacement impact, validate mapping kind/domain/range/coverage, and invalidate affected draft builds/evidence. Keep the adapter independent of a future triplestore.
- [x] **Step 4: Run `.venv/bin/python -m pytest tests/integration/test_ontology.py -v`.** Expect all task assertions to pass; also run preceding task tests when their contracts change.
- [x] **Step 5: Review the diff and commit only this task's files.** Use commit message `feat: versioned rdf ontology, shapes, and explicit mappings`. Record executed checks and any blockers before moving forward.

### Task 4: Compatible embeddings and isolated vector retrieval

**Files:** Create `app/adapters/embeddings.py; app/features/retrieval/{models,schemas,service,routes}.py; app/features/processing/embedding_stage.py; alembic/versions/004_embeddings.py`. Test `tests/integration/test_retrieval.py`. Paths follow the backend/frontend roots above; braces enumerate individual modules.

**Interfaces:** Consumes ModelRef, Evidence, RevisionRef, chunk snapshots. Produces EmbeddingProvider.embed(texts: list[str], model: ModelRef) -> list[list[float]]; search_vector(session, ref: RevisionRef, model: ModelRef, query: str, limit: int) -> list[RetrievalHit]. POST /products/{id}/retrieval; GET/PUT /products/{id}/retrieval-config; POST /products/{id}/evaluation-cases.

- [x] **Step 1: Write failing tests in `tests/integration/test_retrieval.py` with these assertions.**

```python
assert len(real_embedding) == 384
assert wrong_dimension.status_code == 422
assert wrong_model.status_code == 409
assert all(hit.product_id == requested_product for hit in hits)
assert all(hit.revision_id == requested_revision for hit in hits)
assert cited.text == source_text[cited.start:cited.end]
assert unavailable_provider.code == "embedding_provider_unavailable"
```

- [x] **Step 2: Run `.venv/bin/python -m pytest tests/integration/test_retrieval.py -v`.** Expect the named tests to fail because the behavior is absent; infrastructure setup failures do not count as a meaningful red test.
- [x] **Step 3: Implement the interfaces in the listed files.** Pin the resolved all-MiniLM-L6-v2 model revision and cache it explicitly. Embed/query using identical model identity and 384-dimensional vectors. Implement filtered pgvector ranking and release/draft resolution; no lexical fallback. Save evaluation cases and detailed retrieval diagnostics. Separate real-provider integration tests from deterministic unit doubles.
- [x] **Step 4: Run `.venv/bin/python -m pytest tests/integration/test_retrieval.py -v`.** Expect all task assertions to pass; also run preceding task tests when their contracts change.
- [x] **Step 5: Review the diff and commit only this task's files.** Use commit message `feat: compatible embeddings and isolated vector retrieval`. Record executed checks and any blockers before moving forward.

### Task 5: Scoped instance builds and knowledge exploration

**Files:** Create `app/adapters/graph.py; app/features/graph/{models,schemas,service,routes}.py; app/features/processing/graph_stage.py; alembic/versions/005_graph.py; fixtures/graph/extraction-rules.json`. Test `tests/integration/test_graph.py`. Paths follow the backend/frontend roots above; braces enumerate individual modules.

**Interfaces:** Consumes RevisionRef, MappingVersion, OntologyVersion, Evidence. Produces GraphAdapter.build(ref: RevisionRef, build_id: UUID, instances: list[InstanceInput], relationships: list[RelationshipInput]) -> GraphBuild; search(build: GraphBuild, query: str, entity_type: str | None, limit: int) -> list[EntityDetail]; neighbors(build: GraphBuild, entity_id: str, limit: int) -> Neighborhood. GET /products/{id}/entities; GET /entities/{id}; GET /entities/{id}/neighbors; POST /entities/{id}/flags.

- [x] **Step 1: Write failing tests in `tests/integration/test_graph.py` with these assertions.**

```python
assert all(entity.build_id == selected_build for entity in results)
assert neighborhood.node_count <= requested_limit
assert entity.evidence.chunk_id == fixture_chunk.id
assert invalid_mapping.build_state == "blocked"
assert retry.build_id == first.build_id
assert graph_mode.enabled and hybrid_mode.enabled
```

- [x] **Step 2: Run `.venv/bin/python -m pytest tests/integration/test_graph.py -v`.** Expect the named tests to fail because the behavior is absent; infrastructure setup failures do not count as a meaningful red test.
- [x] **Step 3: Implement the interfaces in the listed files.** Build isolated immutable FalkorDB graphs with explicit fixture rules and mapped vocabulary. Record evidence and extraction version on instances and relationships. Implement bounded lookup and neighborhoods with safe query parameters, review flags, graph retrieval and hybrid evidence expansion. Enable modes only after working adapter integration checks.
- [x] **Step 4: Run `.venv/bin/python -m pytest tests/integration/test_graph.py -v`.** Expect all task assertions to pass; also run preceding task tests when their contracts change.
- [x] **Step 5: Review the diff and commit only this task's files.** Use commit message `feat: scoped instance builds and knowledge exploration`. Record executed checks and any blockers before moving forward.

### Task 6: Quality, current reviews, and atomic release activation

**Files:** Create `app/features/evaluations/{models,schemas,service,routes}.py; app/features/reviews/{models,schemas,service,routes}.py; app/features/releases/{models,schemas,service,routes}.py; alembic/versions/006_governance.py`. Test `tests/integration/test_governance.py`. Paths follow the backend/frontend roots above; braces enumerate individual modules.

**Interfaces:** Consumes all versioned inputs and adapters. Produces evaluate(session, ref: RevisionRef) -> EvaluationRun; submit_review(session, ref: RevisionRef, summary: str) -> ReviewDetail; decide_review(session, review_id: UUID, decision: str, reason: str, reviewer_id: UUID) -> ReviewDetail; prepare_release(session, ref: RevisionRef) -> ReleaseManifest; activate_release(session, manifest: ReleaseManifest) -> ReleaseDetail. POST /products/{id}/evaluations; GET /reviews; POST /products/{id}/reviews; POST /reviews/{id}/decision; POST /products/{id}/releases.

- [x] **Step 1: Write failing tests in `tests/integration/test_governance.py` with these assertions.**

```python
assert missing_inputs.state == "insufficient_data"
assert edited_evaluation.state == "stale"
assert edited_review.state == "superseded"
assert stale_publish.status_code == 409
assert failed_prepare.active_release_id == previous_release.id
assert manifest.ontology_sha256 == evaluated.ontology_sha256
assert concurrent_activation.status_code == 409
```

- [x] **Step 2: Run `.venv/bin/python -m pytest tests/integration/test_governance.py -v`.** Expect the named tests to fail because the behavior is absent; infrastructure setup failures do not count as a meaningful red test.
- [x] **Step 3: Implement the interfaces in the listed files.** Persist seven separate measured dimensions with thresholds and linked findings. Capture deterministic input fingerprints and diff snapshots. Reject stale approvals, incomplete readiness and generation races. Prepare and verify immutable manifests, then activate using a locked PostgreSQL transaction. Inject storage and graph preparation failures to prove rollback preserves active release.
- [x] **Step 4: Run `.venv/bin/python -m pytest tests/integration/test_governance.py -v`.** Expect all task assertions to pass; also run preceding task tests when their contracts change.
- [x] **Step 5: Review the diff and commit only this task's files.** Use commit message `feat: quality, current reviews, and atomic release activation`. Record executed checks and any blockers before moving forward.

### Task 7: Consumers, lineage, and actionable overview

**Files:** Create `app/features/consumers/{models,schemas,service,routes}.py; app/features/lineage/{schemas,service,routes}.py; app/features/overview/{schemas,service,routes}.py; alembic/versions/007_consumers.py; scripts/seed.py; scripts/reset.py`. Test `tests/integration/test_consumers.py`. Paths follow the backend/frontend roots above; braces enumerate individual modules.

**Interfaces:** Consumes ReleaseDetail and versioned provenance. Produces resolve_consumer(session, consumer_id: UUID) -> ReleaseDetail; lineage(session, product_id: UUID, release_id: UUID | None) -> LineageGraph; overview(session) -> OverviewDetail. GET/POST/PATCH /consumers; GET /products/{id}/lineage; GET /overview. ConsumerInput supports agent, copilot, API application, dashboard and active/pinned release policies.

- [x] **Step 1: Write failing tests in `tests/integration/test_consumers.py` with these assertions.**

```python
assert pinned_after_publish.release_id == pinned_before_publish.release_id
assert tracking_after_publish.release_id == new_release.id
assert lineage.chunk.document_id == original_document.id
assert lineage.graph.ontology_version == manifest.ontology_version
assert resolved_issue.id not in updated_overview.attention_ids
assert usage.label == "Simulated demo usage"
```

- [x] **Step 2: Run `.venv/bin/python -m pytest tests/integration/test_consumers.py -v`.** Expect the named tests to fail because the behavior is absent; infrastructure setup failures do not count as a meaningful red test.
- [x] **Step 3: Implement the interfaces in the listed files.** Persist consumer associations and policies. Build lineage from actual artifact references, including ontology/mapping dependencies, with graph and table DTOs. Compute attention actions and readiness from persisted records. Add repeatable seed/reset tooling with explicit project namespace boundaries and synthetic fixtures.
- [x] **Step 4: Run `.venv/bin/python -m pytest tests/integration/test_consumers.py -v`.** Expect all task assertions to pass; also run preceding task tests when their contracts change.
- [x] **Step 5: Review the diff and commit only this task's files.** Use commit message `feat: consumers, lineage, and actionable overview`. Record executed checks and any blockers before moving forward.

### Task 8: Application shell, catalog, creation, and document workspace

**Files:** Create `frontend/package.json; frontend/vite.config.ts; frontend/tsconfig.json; frontend/src/api/client.ts; frontend/src/components/{Shell,StatusLabel,DataTable,Dialog,Drawer}.tsx; frontend/src/features/{overview,products,sources,documents,processing}/; design/`. Test `frontend/tests/e2e/frontend_core.spec.ts`. Paths follow the backend/frontend roots above; braces enumerate individual modules.

**Interfaces:** Consumes tasks 1, 2 and 7 API DTOs. Produces shared AppShell, typed client, product/revision selectors and route layout; routes /overview, /products, /products/new, /products/:id, /sources. Product tabs route under /products/:id/:tab; search/filter/sort persist in URL.

- [x] **Step 1: Write failing tests in `frontend/tests/e2e/frontend_core.spec.ts` with these assertions.**

```typescript
await expect(page.getByText("Draft created")).toBeVisible()
await page.reload()
await expect(page.getByText(createdName)).toBeVisible()
await expect(page.getByText("Registered source")).toBeVisible()
await expect(page.getByText("Retry failed stage")).toBeEnabled()
await expect(page.getByLabel("Product lifecycle")).toBeVisible()
```

- [x] **Step 2: Run `npx playwright test tests/e2e/frontend_core.spec.ts`.** Expect the named tests to fail because the behavior is absent; infrastructure setup failures do not count as a meaningful red test.
- [x] **Step 3: Implement the interfaces in the listed files.** Run 12ui draft with at least four concepts, inspect images, choose direction, branch app states with HTML prototype, retain exports as baseline. Implement ten-item shell, overview, catalog filters/sorting, five-step creation allowing incomplete draft, product overview and tabs, source registration/fixture sync, upload/detail split pane, stage monitor/retry and activity. Provide accessible responsive states; wire all actions to persistence.
- [x] **Step 4: Run `npx playwright test tests/e2e/frontend_core.spec.ts`.** Expect all task assertions to pass; also run preceding task tests when their contracts change.
- [x] **Step 5: Review the diff and commit only this task's files.** Use commit message `feat: application shell, catalog, creation, and document workspace`. Record executed checks and any blockers before moving forward.

### Task 9: Semantic, explorer, governance, retrieval, and lineage interfaces

**Files:** Create `frontend/src/features/{ontology,graph,health,reviews,retrieval,lineage,consumers,releases}/; frontend/tests/e2e/workflows.spec.ts; frontend/tests/e2e/accessibility.spec.ts`. Test `frontend/tests/e2e/frontend_workflows.spec.ts`. Paths follow the backend/frontend roots above; braces enumerate individual modules.

**Interfaces:** Consumes tasks 3–7 APIs and task 8 components. Produces remaining primary routes /ontology, /explorer, /health, /reviews, /retrieval, /lineage, /consumers and matching product tabs.

- [x] **Step 1: Write failing tests in `frontend/tests/e2e/frontend_workflows.spec.ts` with these assertions.**

```typescript
await expect(page.getByText("Exactly one complaint identifier")).toBeVisible()
await expect(page.getByText("Impact preview")).toBeVisible()
await expect(page.getByText("Evidence")).toBeVisible()
await expect(page.getByText("Evaluation stale")).toBeVisible()
await expect(page.getByRole("button", {name:"Publish"})).toBeDisabled()
await expect(page.getByText("Pinned release")).toBeVisible()
```

- [x] **Step 2: Run `npx playwright test tests/e2e/frontend_workflows.spec.ts`.** Expect the named tests to fail because the behavior is absent; infrastructure setup failures do not count as a meaningful red test.
- [x] **Step 3: Implement the interfaces in the listed files.** Extend approved 12ui states for three-pane ontology editor and RDF import/export/mapping/shape views, instance canvas plus table/drawer, health metrics and findings, review diffs/decisions, release activity, retrieval modes/evidence/diagnostics/saved cases, lineage graph/table and consumers. Implement destructive-change previews and focus management. Compare each completed route against its approved image using 12ui improve --target, apply kits and inspect wide/narrow layouts.
- [x] **Step 4: Run `npx playwright test tests/e2e/frontend_workflows.spec.ts`.** Expect all task assertions to pass; also run preceding task tests when their contracts change.
- [x] **Step 5: Review the diff and commit only this task's files.** Use commit message `feat: semantic, explorer, governance, retrieval, and lineage interfaces`. Record executed checks and any blockers before moving forward.

### Task 10: Full acceptance journey and delivery documentation

**Files:** Create `tests/acceptance/test_release_journey.py; frontend/tests/e2e/full-journey.spec.ts; README.md; docs/adapters.md; docs/troubleshooting.md; Makefile; scripts/verify.sh`. Test `tests/acceptance/test_release_journey.py`. Paths follow the backend/frontend roots above; braces enumerate individual modules.

**Interfaces:** Consumes all prior contracts. Produces documented commands make up, migrate, seed, test, test-integration, test-e2e, reset, and dev; local preview URL and verification report.

- [x] **Step 1: Write failing tests in `tests/acceptance/test_release_journey.py` with these assertions.**

```python
assert created_product.reload().id == created_product.id
assert published_manifest.id == consumer.resolve().id
assert retrieval[0].evidence.document_id == uploaded_document.id
assert old_release_survives_failed_prepare
assert stale_approval_blocked
await expect(page.getByText("Published release")).toBeVisible()
await expect(page.getByRole("link", {name:"Open source"})).toBeVisible()
```

- [x] **Step 2: Run `.venv/bin/python -m pytest tests/acceptance/test_release_journey.py -v`.** Expect the named tests to fail because the behavior is absent; infrastructure setup failures do not count as a meaningful red test.
- [x] **Step 3: Implement the interfaces in the listed files.** Run all 15 acceptance cases from spec section 18 against real services, plus browser creation→upload→ontology/mapping→processing→evaluation→review→publication→retrieval. Verify restart persistence and reset reproducibility. Document adapter extension points, supported constraints, local model installation, fixture provenance, service failures and demo identity limitations. Start local preview and verify routes; record exact test outcomes and unresolved blockers without claiming unexecuted checks passed.
- [x] **Step 4: Run `.venv/bin/python -m pytest tests/acceptance/test_release_journey.py -v`.** Expect all task assertions to pass; also run preceding task tests when their contracts change.
- [x] **Step 5: Review the diff and commit only this task's files.** Use commit message `feat: full acceptance journey and delivery documentation`. Record executed checks and any blockers before moving forward.

## Acceptance coverage

Spec section 18 maps to tasks: product/revision persistence (1); MinIO originals and failed processing/retries (2); RDF round trips, IRIs, namespaces, mappings and SHACL findings (3); model/dimension compatibility and vector isolation/citations (4); graph isolation/evidence (5); invalidation, stale approvals and failed release preparation (3 and 6); consumer pinning/lineage (7); full browser journey (8–10). Task 10 reruns the integrated suite across all boundaries.

## Self-review

All six phases and ten primary destinations have owning tasks. Backend adapter contracts are defined before consumers; shared DTOs use identical names across tasks. Review-focus failure cases appear in the owning test assertions. No implementation begins until the user reviews this plan and chooses its execution method.
