# Verification record

Date: October 6, 2026. All results below refer to this implementation worktree; the local preview uses the real loopback services.

| Check | Executed result |
|---|---|
| Backend integration and real-model acceptance | 28 tests passed in the latest pre-review run; PostgreSQL/pgvector, MinIO, FalkorDB, RDFLib, pySHACL, and the pinned local model were exercised. |
| Browser workflows | Four Playwright tests passed: creation/reload, all primary destinations, dashboard accessibility plus 390px overflow/navigation, and creation through preparation/checks/review/publication/cited retrieval. |
| Frontend production build | TypeScript and Vite passed. |
| Fresh migration chain | Alembic 001–008 applied successfully to a blank `knowledge_migration_check` database. |
| Source formats | Text, PDF, and DOCX originals retrieved byte-for-byte and extracted into cited excerpts; active HTML cannot be served from a text upload. |
| Infrastructure health | Actual PostgreSQL, MinIO, and FalkorDB probes reported ready. |
| Design verification | Nine original 12ui screens and HTML exports retained; target kits generated. Safe shared typography/surface/icon changes applied semantically. DOM overlap is low where actual business workflows differ from static reference states. No pixel-perfect fidelity claim is made. |

The standalone worker was also tested in a separate Python process, catching and fixing an import-registration issue that API-imported tests could not expose. Other observed failures—form accessible names, status contrast, RDF conflicts, and used-definition impact—have dedicated regression coverage.

The backend acceptance journey used actual 384-dimensional model vectors and semantic paraphrase retrieval, with hybrid relationships and exact document citations. Deterministic embedding doubles are used only in focused isolation/compatibility tests. Those doubles do not stand in for the real-model acceptance result.

Container image verification and final independent review results are recorded after completion below. CPU-only PyTorch is selected for Linux so a local MVP does not download CUDA libraries.

Limits: this is a local single-workspace MVP with synthetic identities, fixture-backed fact extraction, registered external sources, and simulated consumer usage. Production authentication, live external connectors, unrestricted OWL reasoning, remote SPARQL, and generated LLM answers are intentionally outside scope. Browser tests add inspectable QA products to the live demo; backend tests use a separate database.
