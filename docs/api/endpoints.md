# Generated endpoint reference

Generated from FastAPI routes. Run `make docs` to refresh or `make docs-check` to detect drift.
This lists declared request contracts; see [API guide](../api.md) for wire behavior and response limits.
Private agent gateway routes are intentionally excluded from OpenAPI.

| Method | Path | Parameters | Body | Declared responses |
|---|---|---|---|---|
| GET | `/api/chat/status` | — | — | 200 |
| GET | `/api/consumers` | `product_id` (query) | — | 200, 422 |
| POST | `/api/consumers` | — | `application/json` → `ConsumerInput` | 201, 422 |
| PATCH | `/api/consumers/{id}` | `id` (path, required) | `application/json` → `ConsumerInput` | 200, 422 |
| GET | `/api/consumers/{id}/resolve` | `id` (path, required) | — | 200, 422 |
| GET | `/api/documents/{id}` | `id` (path, required) | — | 200, 422 |
| GET | `/api/documents/{id}/original` | `id` (path, required) | — | 200, 422 |
| GET | `/api/health` | — | — | 200 |
| POST | `/api/imports/preview` | — | `multipart/form-data` → `Body_preview_import_api_imports_preview_post` | 200, 422 |
| POST | `/api/jobs/{id}/retry` | `id` (path, required) | — | 200, 422 |
| POST | `/api/onboarding` | — | `multipart/form-data` → `Body_onboard_api_onboarding_post` | 201, 422 |
| GET | `/api/overview` | — | — | 200 |
| GET | `/api/products` | `q` (query), `domain` (query), `owner` (query), `state` (query), `sort` (query), `offset` (query), `limit` (query) | — | 200, 422 |
| POST | `/api/products` | — | `application/json` → `ProductCreate` | 201, 422 |
| GET | `/api/products/{id}` | `id` (path, required) | — | 200, 422 |
| PATCH | `/api/products/{id}` | `id` (path, required) | `application/json` → `ProductUpdate` | 200, 422 |
| GET | `/api/products/{id}/activity` | `id` (path, required) | — | 200, 422 |
| POST | `/api/products/{id}/chat` | `id` (path, required), `preview` (query), `revision_id` (query), `release_id` (query), `conversation_id` (query), `request_id` (query) | `application/json` → `ChatInput` | 200, 422 |
| GET | `/api/products/{id}/chat/runs/{request_id}` | `id` (path, required), `request_id` (path, required) | — | 200, 422 |
| GET | `/api/products/{id}/documents` | `id` (path, required), `revision_id` (query) | — | 200, 422 |
| POST | `/api/products/{id}/documents` | `id` (path, required), `revision_id` (query), `source_id` (query) | `multipart/form-data` → `Body_upload_api_products__id__documents_post` | 201, 422 |
| POST | `/api/products/{id}/draft` | `id` (path, required) | — | 200, 422 |
| GET | `/api/products/{id}/entities` | `id` (path, required), `q` (query), `entity_type` (query), `revision_id` (query), `limit` (query) | — | 200, 422 |
| POST | `/api/products/{id}/entities/{entity_id}/flags` | `id` (path, required), `entity_id` (path, required), `revision_id` (query) | `application/json` → `FlagInput` | 201, 422 |
| GET | `/api/products/{id}/entities/{entity_id}/neighbors` | `id` (path, required), `entity_id` (path, required), `revision_id` (query), `limit` (query) | — | 200, 422 |
| POST | `/api/products/{id}/evaluation-cases` | `id` (path, required) | `application/json` → `CaseInput` | 200, 422 |
| GET | `/api/products/{id}/evaluations` | `id` (path, required), `revision_id` (query) | — | 200, 422 |
| POST | `/api/products/{id}/evaluations` | `id` (path, required), `revision_id` (query) | — | 200, 422 |
| POST | `/api/products/{id}/graph/build` | `id` (path, required), `revision_id` (query) | — | 200, 422 |
| GET | `/api/products/{id}/lineage` | `id` (path, required), `release_id` (query), `revision_id` (query) | — | 200, 422 |
| GET | `/api/products/{id}/ontology` | `id` (path, required), `revision_id` (query) | — | 200, 422 |
| PATCH | `/api/products/{id}/ontology` | `id` (path, required), `revision_id` (query) | `application/json` → `OntologyEdit` | 200, 422 |
| GET | `/api/products/{id}/ontology/export` | `id` (path, required), `revision_id` (query) | — | 200, 422 |
| POST | `/api/products/{id}/ontology/impact` | `id` (path, required), `revision_id` (query) | `application/json` → `ImportInput` | 200, 422 |
| POST | `/api/products/{id}/ontology/import` | `id` (path, required), `revision_id` (query) | `application/json` → `ImportInput` | 200, 422 |
| PUT | `/api/products/{id}/ontology/mapping` | `id` (path, required), `revision_id` (query) | `application/json` → `MappingInput` | 200, 422 |
| POST | `/api/products/{id}/ontology/preview-edit` | `id` (path, required), `revision_id` (query) | `application/json` → `OntologyEdit` | 200, 422 |
| POST | `/api/products/{id}/ontology/starter` | `id` (path, required), `revision_id` (query) | `application/json` → `StarterInput` | 200, 422 |
| POST | `/api/products/{id}/ontology/validate-sample` | `id` (path, required), `revision_id` (query) | `application/json` → `SampleInput` | 200, 422 |
| GET | `/api/products/{id}/processing` | `id` (path, required), `revision_id` (query) | — | 200, 422 |
| POST | `/api/products/{id}/processing/run` | `id` (path, required), `revision_id` (query) | — | 200, 422 |
| GET | `/api/products/{id}/releases` | `id` (path, required) | — | 200, 422 |
| POST | `/api/products/{id}/releases` | `id` (path, required) | — | 201, 422 |
| GET | `/api/products/{id}/releases/{release_id}` | `id` (path, required), `release_id` (path, required) | — | 200, 422 |
| POST | `/api/products/{id}/retrieval` | `id` (path, required) | `application/json` → `RetrievalInput` | 200, 422 |
| GET | `/api/products/{id}/retrieval-config` | `id` (path, required) | — | 200, 422 |
| PUT | `/api/products/{id}/retrieval-config` | `id` (path, required) | `application/json` → `ConfigInput` | 200, 422 |
| POST | `/api/products/{id}/reviews` | `id` (path, required), `revision_id` (query) | `application/json` → `SubmitInput` | 200, 422 |
| GET | `/api/reviews` | `product_id` (query) | — | 200, 422 |
| POST | `/api/reviews/{id}/decision` | `id` (path, required) | `application/json` → `DecisionInput` | 200, 422 |
| GET | `/api/sources` | — | — | 200 |
| POST | `/api/sources` | — | `application/json` → `SourceInput` | 201, 422 |
| POST | `/api/sources/test` | — | `application/json` → `SourceInput` | 200, 422 |
| POST | `/api/sources/{id}/sync` | `id` (path, required) | — | 200, 422 |
| POST | `/api/sources/{id}/sync-fixture` | `id` (path, required) | — | 200, 422 |
| POST | `/api/sources/{id}/test` | `id` (path, required) | — | 200, 422 |
