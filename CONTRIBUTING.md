# Contributing

Start with the [README](README.md), [architecture](docs/architecture.md), and [data model](docs/data-model.md). This project is a local MVP with explicit evidence/version guarantees. Preserve those guarantees when extending a feature.

## Development setup

Use Python 3.12 through uv, Node 22.x at 22.12+, 24.x, or 26+ (Node 24 recommended), npm, Docker Compose v2, and make. Install dependencies with `make install`; start storage, migrate, download the pinned model, and seed as described in README. Run API/worker/frontend in separate terminals or choose the container API/worker path.

Create a feature branch for changes. The repository supplies dependency locks but no hosted CI workflow yet; run required checks locally. Do not add local `.env`, databases, object exports, backups, node_modules, model caches, or generated build/test output to commits. Use synthetic fixtures for reproducible examples.

## Code organization and invariants

- Feature route modules validate requests and resolve sessions/scope; service modules own workflow behavior.
- External storage, graph, embedding, ontology, and source I/O belong behind adapters.
- Use explicit revision/release identity for evidence reads. Avoid defaulting a published read to a new draft.
- Editable mutations lock the revision and honor expected generations where supported. Published revisions stay immutable.
- Active source snapshots participate in preparation, facts, vectors, checks, and publication; superseded draft data must not leak into them.
- Preserve evidence offsets, original URLs, processing/model identities, and graph-build scope.
- Evaluation/review fingerprints must capture relevant inputs. Old approvals must not authorize changed data.
- External side effects may survive SQL rollback; keep artifact/build identities deterministic and retries safe.
- Session dependencies use function scope so transaction completion precedes success responses.
- Keep user-facing copy in business terms; technical RDF/mapping representation belongs in advanced views.

For database changes, add an Alembic migration and verify a fresh install plus upgrade. Some historical migrations import ORM models; exclude future-added columns from earlier table creation to prevent duplicate columns. Keep migration-only indexes in the data model documentation. Do not replace the migration workflow with `create_all()`.

## Tests and checks

| Change | Appropriate checks |
|---|---|
| Business service/schema/adapter | Relevant backend regression tests; full `make test` when cross-feature behavior changes. |
| UI workflow/state/accessibility | `make check-ui`, relevant Playwright tests against a running local stack; `make build`; full browser suite when shared navigation/context changes. |
| Agent/gateway integration | Scoped retrieval and metadata tests, tool restrictions, stream ownership/cancellation, sanitized errors, and explicit real-provider acceptance if needed. |
| Routes/ORM models/docs | `make docs`, `make docs-check`, link and example review. |
| Migration | Fresh chain and upgraded database verification against local test infrastructure. |

```sh
make test
make check-ui
make test-e2e
make build
make docs-check
```

`make test` initializes `knowledge_test`; fixtures configure isolated relational metadata. Real adapter/model tests need local storage and the downloaded model. `make test-fast` excludes the actual-model-marked journey but still needs services. Browser tests use the demo workspace and leave inspectable synthetic products.

Focused Python lint can be run with `backend/.venv/bin/ruff check <changed paths>`. Existing legacy modules do not all pass an expanded whole-repository rule set; distinguish a focused passing check from a global lint claim. Frontend verification uses Prettier, strict TypeScript, Vitest/React Testing Library, Vite, and Playwright. No separate ESLint script is configured. See the [frontend strategy](docs/frontend-strategy.md) for module ownership and the data-handling contract. Use `npm run test:unit:watch --prefix frontend` for fast iteration and `npm run preview --prefix frontend` to inspect the production build. Keep browser and tooling type checks separate; share runtime aliases through `frontend/tooling/paths.ts`.

Do not use provider stubs as evidence of real agent compatibility. Real provider tests are optional, require an explicitly supplied server credential, can incur usage, and should use synthetic evidence. The committed tests do not need a provider key. Record exact executed results and limitations in `docs/verification.md` when adding a substantial feature.

## Documentation maintenance

`scripts/export_reference.py` imports FastAPI/SQLAlchemy metadata without connecting to services or calling providers. From the root:

```sh
make docs
make docs-check
```

Generated files are `docs/api/openapi.json`, `docs/api/endpoints.md`, and `docs/reference/database.md`. Commit them with route/model changes. Do not hand-edit those files; update the code or generator. Keep response/media-type caveats in the human API guide until explicit response schemas cover them. Validate relative Markdown links and keep diagrams consistent with actual storage/transaction boundaries.

## Dependencies and AI integration

Use `uv sync --project backend --python 3.12 --extra test --extra embeddings` and the checked-in lock. Container `requirements.lock` must be refreshed when backend dependencies change; Linux uses the pinned CPU PyTorch index. Use `npm ci --prefix frontend` for frontend installation. Preserve `.npmrc`, React deduplication, the Blume virtual module alias, and the compatible routing override unless an upgrade proves them unnecessary.

Claude Agent SDK and LiteLLM are pinned because the gateway relies on concrete adapter/runtime contracts and explicit provider-stream closure. Upgrades require a deliberate compatibility review. Do not forward provider secrets to the frontend, enable unrestricted built-in agent tools, or render generated HTML/actions. Presentation components must remain validated and citation-bound.

## Change descriptions

Explain the concrete trigger, resulting behavior, why the change is needed, and what you tested. Include material limitations. Use the existing specification/decision records as historical context, not proof that unimplemented functionality exists. No project license has been selected; do not add a license or assert licensing terms without the repository owner's decision.
