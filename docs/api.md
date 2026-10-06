# API guide

The public API is served by FastAPI at `http://127.0.0.1:58000`. Business paths start with `/api`; interactive documentation is at `/docs` and `/redoc`, and the live schema is at `/openapi.json`.

The checked-in [OpenAPI 3.1 specification](api/openapi.json) and [endpoint inventory](api/endpoints.md) are generated from the application. Refresh with `make docs`; verify with `make docs-check`. They contain 47 paths and 56 operations. Internal agent gateway routes are excluded.

## Contract conventions

- Requests use JSON unless a route explicitly accepts multipart file/form data.
- IDs are UUID-shaped strings. Chat conversation/request IDs are validated UUIDs.
- Creation responses commonly return 201; action routes commonly return 200. No global response envelope is imposed.
- The product catalog returns `{items,total,offset,limit}`. Other list endpoints often return arrays; entities return `{items,build}`. Pagination is route-specific.
- The local API has no authentication or authorization layer. Demo reviewer fields are workflow simulation, not identity proof.
- SQL session dependencies commit before returning a successful response. Errors roll back relational mutations.
- Product configuration validates finite quality thresholds (0–1), matching-result limits (1–50), and complete embedding-model identity before persistence. Search model overrides use a typed request schema. Source credentials and model keys are server environment values. Never place secrets in source `config`, frontend variables, or chat payloads.

**Schema limits:** many handlers return untyped dictionaries or ORM objects. Their response schemas in OpenAPI are generic, and runtime 409/503 errors may not be declared. The generated schema also declares generic success JSON on some handlers that actually return bytes or a text stream. Actual media types for original documents, Turtle export, and chat are described below. Requests have stronger typed validation than most responses. This document describes implemented behavior rather than promising a fully typed client SDK.

## Revision and release scope

Many product routes accept an optional `revision_id` query parameter. Without it, the server selects the latest non-published revision and can return `draft_required` if no draft exists. Supply a revision explicitly when inspecting historical published documents, concepts, processing, entities, evaluations, or lineage.

Mutations require an editable revision. Product updates require `expected_generation`; supported ontology/mapping edits also accept it. Refresh the product after a mutation to obtain the new generation rather than reusing an old counter.

Retrieval uses body fields `preview`, `revision_id`, and `release_id`. Chat uses those fields as query parameters. With `preview=false`, the product's active release is the default; an explicit release must belong to that product. With `preview=true`, the selected revision's current active evidence is used. `revision_id` alone does not select draft preview in retrieval/chat. Consumer resolution uses its own active/pinned policy.

## Start a product and import a file

These shell examples run from the repository root with API, worker, and storage running. `jq` is used only to read response IDs. They create a synthetic product in the local workspace.

```sh
BASE=http://127.0.0.1:58000
PRODUCT_ID=$(curl --fail-with-body -sS "$BASE/api/products" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Support Knowledge","purpose":"Trusted refund guidance","domain":"Support","owner":"Demo author"}' \
  | jq -r '.id')

curl --fail-with-body -sS "$BASE/api/products/$PRODUCT_ID/ontology/starter" \
  -H 'Content-Type: application/json' -d '{"template":"customer-support"}'

curl --fail-with-body -sS "$BASE/api/imports/preview" \
  -F 'file=@fixtures/documents/complaints.txt'

curl --fail-with-body -sS "$BASE/api/products/$PRODUCT_ID/documents" \
  -F 'file=@fixtures/documents/complaints.txt'
```

Supported upload formats are PDF, DOCX, text, Markdown, CSV, JSON records, and Turtle. Each file is bounded to 20 MB, with narrower structured/RDF limits. The preview endpoint validates without creating a document. Upload responses include document/source/artifact state and processing information; they do not mean that graph preparation is complete.

To create everything in one onboarding transaction, use a JSON string in the `metadata` multipart field and optional repeated `files` fields:

```sh
curl --fail-with-body -sS "$BASE/api/onboarding" \
  -F 'metadata={"name":"Support Workspace","purpose":"Support answers","domain":"Support","owner":"Demo author","template":"customer-support"}' \
  -F 'files=@fixtures/documents/complaints.txt'
```

`template` is `general`, `customer-support`, or `empty`. Metadata can also include `config`, a new `source` or `existing_source_id`, and `import_source_now`. These nested fields are encoded in the metadata JSON string, not separate form fields. Invalid input rolls back relational creation. Content-addressed objects written before failure can remain unreferenced.

## Prepare, check, review, publish

```sh
curl --fail-with-body -sS -X POST "$BASE/api/products/$PRODUCT_ID/processing/run"
curl --fail-with-body -sS "$BASE/api/products/$PRODUCT_ID/processing"
```

The first call enqueues stage work. Poll processing until document/revision jobs finish; do not interpret `state=queued` as completion. Start the worker and investigate/retry failed jobs before continuing.

```sh
curl --fail-with-body -sS -X POST "$BASE/api/products/$PRODUCT_ID/evaluations"

REVIEW_ID=$(curl --fail-with-body -sS "$BASE/api/products/$PRODUCT_ID/reviews" \
  -H 'Content-Type: application/json' -d '{"summary":"Initial support release"}' \
  | jq -r '.id')

curl --fail-with-body -sS "$BASE/api/reviews/$REVIEW_ID/decision" \
  -H 'Content-Type: application/json' \
  -d '{"decision":"approve","reason":"Evidence checked","reviewer_id":"demo-reviewer"}'

curl --fail-with-body -sS -X POST "$BASE/api/products/$PRODUCT_ID/releases"
```

Review submission and publication return 409 unless checks/approval refer to current passing inputs. Rejection requires a reason. Editing or freshness expiry can supersede a review. The `demo-reviewer` value simulates a separate reviewer and is not a security boundary. To update a published product, call `POST /api/products/{id}/draft` first.

Example metadata update:

```sh
curl --fail-with-body -sS -X POST "$BASE/api/products/$PRODUCT_ID/draft"
GENERATION=$(curl --fail-with-body -sS "$BASE/api/products/$PRODUCT_ID" | jq '.draft.generation')
curl --fail-with-body -sS -X PATCH "$BASE/api/products/$PRODUCT_ID" \
  -H 'Content-Type: application/json' \
  -d "{\"expected_generation\":$GENERATION,\"purpose\":\"Updated support guidance\"}"
```

The first call opens or reuses an editable draft; updating it increments its generation and requires fresh preparation/checks/review before its next publication.

## Search and evidence

```sh
curl --fail-with-body -sS "$BASE/api/products/$PRODUCT_ID/retrieval" \
  -H 'Content-Type: application/json' \
  -d '{"query":"Which customers submitted complaints?","mode":"hybrid","limit":5,"preview":false}'
```

`mode` is `vector`, `graph`, or `hybrid`; `limit` is 1–50, default 5. Vector/hybrid require prepared vectors with the exact selected model identity. A body `model` override must match name/revision/dimension or retrieval fails. Draft search explicitly uses `preview=true` and optionally `revision_id`.

A vector result has this shape (IDs/scores are illustrative):

```json
{
  "results": [{
    "score": 0.82,
    "evidence": {
      "chunk_id": "chunk-uuid",
      "document_id": "document-uuid",
      "text": "Complaint C-1042 submitted by Customer A-203.",
      "start": 0,
      "end": 43,
      "processing_version": "extract-v1/chunk-v1",
      "document_name": "complaints.txt",
      "source_url": "/api/documents/document-uuid/original"
    }
  }],
  "diagnostics": {
    "revision_id": "revision-uuid",
    "generation": 3,
    "release_id": "release-uuid",
    "preview": false,
    "mode": "vector",
    "chunk_snapshot_count": 2
  },
  "label": "Published release"
}
```

Diagnostics also include model identity and elapsed time. Hybrid results add related facts; graph result details differ. Original evidence is fetched through `GET /api/documents/{id}/original`, with content type determined from the supported file extension and sandbox/nosniff response headers. RDF export returns `text/turtle` at `GET /api/products/{id}/ontology/export?revision_id=...`.

## Native sources

Create a PostgreSQL source using a server-defined reference:

```sh
curl --fail-with-body -sS "$BASE/api/sources" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"Sales records\",\"type\":\"postgres\",\"owner\":\"Demo author\",\"product_ids\":[\"$PRODUCT_ID\"],\"config\":{\"credential_env\":\"SOURCE_SALES_DATABASE_URL\",\"schema\":\"public\",\"table\":\"orders\",\"limit\":1000}}"
```

The server must already have `SOURCE_SALES_DATABASE_URL`. `POST /api/sources/test` tests unsaved `SourceInput`; `POST /api/sources/{id}/test` tests a saved source; `POST /api/sources/{id}/sync` imports its snapshot into associated drafts. Associated products must have editable revisions.

For APIs use `type=api`, `location=https://api.example.com/orders`, and `config` such as `{"format":"json","records_path":"data.items","token_env":"SOURCE_CRM_TOKEN","limit":1000}`. The exact origin must appear in `SOURCE_API_ALLOWED_ORIGINS`. No arbitrary passwords/headers/provider URLs belong in config. See [source setup](source-connections.md) for limits. `/sync-fixture` is explicitly synthetic demo data and does not read a remote system.

## Streaming AI chat

First read `GET /api/chat/status`. It returns `configured`, the selected model, `agent`, and `gateway`; it never returns keys. Prepare a product version and configure the server key/token before invoking chat.

```sh
CONVERSATION_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
REQUEST_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
curl --fail-with-body -N -sS \
  "$BASE/api/products/$PRODUCT_ID/chat?conversation_id=$CONVERSATION_ID&request_id=$REQUEST_ID&preview=false" \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Summarize the complaints and cite the sources."}]}'

curl --fail-with-body -sS \
  "$BASE/api/products/$PRODUCT_ID/chat/runs/$REQUEST_ID"
```

The browser-facing POST returns **plain UTF-8 streamed text**, not SSE, JSON Lines, or OpenAI chunks. Headers include `Cache-Control: no-store`, `X-Accel-Buffering: no`, and `X-Chat-Run: <request UUID>`. Fetch the metadata after stream completion (it can also report a still-running state). The packet includes `id`, `state`, revision/release/generation, label, sources, optional generative `ui`, error, and model. Sources have server-assigned `S1`… citation IDs and original evidence URLs. States are `running`, `complete`, `cancelled`, or `failed`.

For a follow-up, reuse the conversation UUID, send the user/assistant history, and generate a **new request UUID**. Only `user` and `assistant` roles are accepted. Limits: 40 messages, 12,000 characters per message, final user question at most 2,000, total content at most 24,000. `page` is optional context accepted for Blume compatibility; it does not grant tools or scope. If UUIDs are omitted the server assigns them and the request UUID is in the response header.

Concurrent requests in one conversation return 409; the process admits at most three active conversations. Abandoned reservations expire after 180 seconds; answer execution has a 120-second cancellation-scope deadline plus SDK cleanup. Up to 500 metadata packets are retained for at most 30 minutes; server restart removes them. There is no persistent chat history. Reusing/guessing a request ID cannot fetch another product's packet, but production user authorization is not implemented.

Errors before streaming starts use normal HTTP statuses. Errors after headers are sent append a generic message to the text and mark metadata `failed`; a 200 stream is not proof of successful generation. A client should check the matching metadata state. Closing the response cancels generation with an SDK cleanup grace period. There is no separate public cancel endpoint.

Generative UI accepts only Col, Row, Card, Fact, Table, and Evidence. It is restricted to depth 6, 60 nodes, 20 KB serialized JSON, at most 8 table columns/30 rows, and known citation identifiers. Model-supplied URLs, actions, arbitrary HTML, or unknown props are rejected.

## Private agent gateway

`POST /internal/llm/v1/messages` and `/internal/llm/v1/messages/count_tokens` serve the Claude SDK's Anthropic-compatible protocol. They require the server `CHAT_GATEWAY_TOKEN` via `x-api-key` or Bearer authorization and are hidden from public OpenAPI. They are not the browser chat API.

The gateway uses a fixed OpenRouter endpoint, the server-selected model, server-only provider key, a 2 MB request limit, up to 1,200 output tokens by default, 40-second provider timeout, and no provider retries. LiteLLM translates input tools/messages and output/stream events. The token-count helper is a conservative byte-based estimate for context sizing, not a billing tokenizer. See [chat design](chat-design.md) for stream ownership and sanitization.

## Errors and operational behavior

FastAPI wraps `HTTPException.detail` as `{ "detail": ... }`. Detail can be a string, a `{code,message}` object, or a validation-error list; there is no universal custom error schema.

| Status | Typical meaning |
|---|---|
| 401 | Private gateway missing/incorrect authentication. Public business routes have no auth gate. |
| 404 | Missing record, wrong product-owned release, missing/expired chat packet. |
| 409 | No editable draft, immutable revision, generation conflict, missing preparation, stale checks/review, concurrent chat turn. |
| 413 | Size limits exceeded on applicable upload/gateway routes. |
| 422 | Request/schema/import/source validation, bad mapping, invalid review decision. |
| 503 | Required storage/model/provider unavailable, publication preparation failed, unconfigured/busy assistant. |

Example conflict:

```json
{"detail":{"code":"generation_conflict","message":"This draft changed. Refresh before saving."}}
```

Do not blindly retry mutating calls after a network timeout: fetch current product/review/release state first. Upload/snapshot/job/build deduplication is input-specific; the API does not implement a general `Idempotency-Key` contract. `/api/health` returns HTTP 200 with per-service `ready`/`unavailable` values, so monitoring must inspect the JSON body. No API version prefix or compatibility policy is established beyond this local MVP; regenerate/reference-check docs with every contract change.

## Rule edit semantics

For ontology edits, omitted or null `parent`, `domain`, and `range` preserve the existing links; an explicit empty string removes the link. A shape edit can supply `original_path` to identify the property being changed while preserving sibling constraints. `max_count: null` means unbounded. Supported cardinalities must be nonnegative integers with minimum no greater than maximum. Malformed rules fail before persistence.
