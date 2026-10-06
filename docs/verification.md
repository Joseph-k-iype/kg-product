# Verification record

Date: October 6, 2026. All results below refer to this implementation worktree; the local preview uses the real loopback services.

| Check | Executed result |
|---|---|
| Backend integration and real-model acceptance | 34 tests passed after the independent-review fix pass; PostgreSQL/pgvector, MinIO, FalkorDB, RDFLib, pySHACL, and the pinned local model were exercised. |
| Browser workflows | Six Playwright tests cover: creation/reload, all primary destinations, dashboard accessibility plus 390px overflow/navigation, creation through preparation/checks/review/publication/cited retrieval, clearing search evidence on product switch, and flagging the inspected published version. |
| Frontend production build | TypeScript and Vite passed. |
| Fresh migration chain | Alembic 001–008 applied successfully to a blank `knowledge_migration_check` database. |
| Source formats | Text, PDF, and DOCX originals retrieved byte-for-byte and extracted into cited excerpts; active HTML cannot be served from a text upload. |
| Infrastructure health | Actual PostgreSQL, MinIO, and FalkorDB probes reported ready. |
| Design verification | Nine original 12ui screens and HTML exports retained; target kits generated. Safe shared typography/surface/icon changes applied semantically. DOM overlap is low where actual business workflows differ from static reference states. No pixel-perfect fidelity claim is made. |

The standalone worker was also tested in a separate Python process, catching and fixing an import-registration issue that API-imported tests could not expose. Other observed failures—form accessible names, status contrast, RDF conflicts, and used-definition impact—have dedicated regression coverage.

The backend acceptance journey used actual 384-dimensional model vectors and semantic paraphrase retrieval, with hybrid relationships and exact document citations. Deterministic embedding doubles are used only in focused isolation/compatibility tests. Those doubles do not stand in for the real-model acceptance result.

Container image verification and final independent review results are recorded after completion below. CPU-only PyTorch is selected for Linux so a local MVP does not download CUDA libraries.

Initial implementation limits: this local single-workspace MVP used synthetic identities, fixture-backed document fact extraction, registered external sources, and simulated consumer usage. The later import update below introduces native PostgreSQL/API readers and structured facts. Production authentication, unrestricted OWL reasoning, remote SPARQL, and generated LLM answers remain outside scope. Browser tests add inspectable QA products to the live demo; backend tests use a separate database.

## Final independent review and container validation

One fresh reviewer inspected the whole branch and found eight Important issues and one Minor issue. All eight Important issues were reproduced with failing tests and fixed. The backend regression suite now covers metadata re-preparation, revision locking during a concurrent edit, freshness expiry, revision-level job failures/retries, published-release lineage, and recovery after an external graph write followed by DB rollback. Browser regressions cover search-context reset and correction-version scoping. The full backend suite passed 34/34 after the fixes.

The Docker image built successfully with torch 2.9.1+cpu. A container connected to all three storage services and loaded the pinned local model, verifying an actual 384-dimensional embedding. CUDA is absent from that image. Fresh migrations and host runtime checks were also executed.

Deferred Minor: impact previews could list more historical shape/evaluation/release dependencies. Current previews expose facts/mappings and required rebuild/check/review steps, and preserve published artifacts.

Final full browser run: **6/6 passed** after context and correction fixes. Final backend run: **34/34 passed**. Frontend production build passed. The final container image was rebuilt with the corrected application source.

Final corrected container smoke: FastAPI returned healthy status and all three storage adapters reported ready.

## Light/red visual redesign

After the user's Nothing/Inter/Geist/shader request, the full browser suite passed **8/8**. The production frontend build passed. New regressions verify unchanged decorative artwork under reduced motion and working dashboard/navigation when GPU access is denied. Both failed before the shader existed, then passed. The accessibility check reproduced a transient opacity/contrast failure, fixed by removing text fades; the full suite subsequently passed. Existing persisted creation, document preparation, quality checks, approvals, publication, cited retrieval, product switching, and correction scoping all still passed. Backend source was unchanged by this redesign.

An independent reviewer also exercised shader pause/resume, offscreen suspension, context loss/restoration, GPU cleanup and font loading, with no Critical or Important findings. Browser captures are under `docs/screenshots/*-red.png`.

## Business onboarding and structured/source imports

Final backend run: **51/51 passed** in 48.49 seconds, including the real-model acceptance journey. Native PostgreSQL and API tests read a real local table and HTTP service; no external business credentials were supplied. Four independent-review findings were reproduced and fixed: current source snapshot replacement, Turtle literal/label fidelity, anonymous identifier scoping, and reuse of existing vocabulary declarations.

Final browser run: **10/10 passed** in 1.1 minutes. It includes mixed CSV/Turtle/document onboarding, recoverable invalid-file errors, readiness explanations, accessibility, narrow navigation, preparation through publishing and cited retrieval, search context, published correction scope, and shader fallbacks. Manual readiness inspection at 390px confirmed no page overflow. All three live storage health probes report ready.

The final Docker image rebuilt successfully with the latest transaction/import source. Container smoke confirmed all three storage probes healthy, a CSV record parsed correctly, and native source modules loaded. Host API/worker and frontend remain running for the local preview.

Fresh migration chain **001–010** applied to a blank `knowledge_import_migration_check` database. Column inspection confirms source configuration, normalized document data, and active-snapshot state. The old 002 migration now excludes columns introduced later, preventing duplicate-column errors during a fresh installation.

The browser journey exposed success responses preceding database commits. Two deterministic ASGI/real-database regressions reproduced both stale reads at response start and a false success on commit failure. Session dependencies now complete transactions before responses using FastAPI's [function dependency scope](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#early-exit-and-scope); both regressions pass. The dependency minimum was raised to the version supporting this scope. A repeated ontology read in dashboard freshness checks was also removed without changing the snapshot contents.

The production frontend build and focused lint checks pass. Readiness and Bring data captures are retained in `docs/screenshots/`. The existing light/red block design and Inter/Geist remain. A free 12ui alignment kit was generated against the existing Purpose target. Font/palette replacements, invented fields, raster branding, decorative side panels, and old step wording were skipped because they conflict with the user's explicit fonts and this simpler functional journey. The target kit contains no extracted raster assets; no fidelity claim is made. New generation was unavailable because the allowance/wallet was exhausted.
