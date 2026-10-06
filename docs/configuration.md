# Configuration

Host API/worker commands run from `backend/` through the root Makefile. Pydantic settings read `../.env` and process environment. The source connector separately reads `SOURCE_*` references from process environment or that same root file. Run these commands from the repository root so relative paths remain consistent.

Create the file with `cp .env.example .env` and restrict local permissions with `chmod 600 .env`. `.env` is ignored. The example contains only local demo defaults and blank optional credentials. Environment values override file values. Do not copy an existing private `.env` into a repository or frontend build.

## Infrastructure and application settings

| Variable | Host default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://knowledge:knowledge-local@localhost:55432/knowledge` | SQLAlchemy metadata and pgvector connection. |
| `MINIO_ENDPOINT` | `localhost:59000` | Host/port without scheme; current adapter uses non-TLS local transport. |
| `MINIO_ACCESS_KEY` | `knowledge` | Local MinIO account. |
| `MINIO_SECRET_KEY` | `knowledge-local` | Local MinIO password. |
| `MINIO_BUCKET` | `knowledge-artifacts` | Created by the object adapter on first write if absent. |
| `GRAPH_URL` | `redis://localhost:56379` | FalkorDB Redis-protocol connection. |
| `MODEL_CACHE` | `./.model-cache` | Relative to the backend working directory in host commands; `/models` in Compose. |
| `CORS_ORIGINS` | See `.env.example` | JSON array of direct browser origins; default code values use port 5173. Vite on 5174 uses a same-origin `/api` proxy, so direct cross-origin access is usually unnecessary. |
| `API_URL` | `http://127.0.0.1:58000` | Vite process environment override for the `/api` proxy target; not a backend setting. |

Compose overrides the API/worker database host to `postgres:5432`, MinIO to `minio:9000`, and graph host to `falkordb:6379`. Its local default accounts remain demo values. Changing application credentials alone does not rotate storage-service credentials; update both sides consistently. Published ports are loopback-bound.

## AI chat settings

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | Blank/unconfigured | Server-only provider key. |
| `CHAT_GATEWAY_TOKEN` | Blank/unconfigured | Random shared secret between Claude Agent SDK and the local Messages gateway. |
| `CHAT_MODEL` | `deepseek/deepseek-v3.2` | OpenRouter model selected by the server; client model overrides are not accepted. |
| `CHAT_GATEWAY_URL` | `http://127.0.0.1:58000/internal/llm` | Host SDK gateway base URL; Compose overrides to `http://127.0.0.1:8000/internal/llm`. |
| `CHAT_MAX_OUTPUT_TOKENS` | `1200` | Server generation cap; request values are clamped by the gateway. |

API settings are loaded at process import: restart the host API after edits. For Compose environment changes, recreate the API, for example `docker compose up -d --force-recreate api`. Do not run the host API on its occupied container port. Source connector file references are reread during host connector operations; container environment changes still require recreation.

The SDK receives a private local gateway credential and model aliases; the actual OpenRouter key is injected only by the gateway. The browser receives availability/model metadata, never these secrets. A blank provider key/token leaves AI chat unconfigured while other business features still work.

## Native source references

Source records accept credential **names**, restricted to `SOURCE_[A-Z0-9_]+`, rather than credential values. These variables are read by the connector, not declared as fixed Pydantic settings.

```dotenv
SOURCE_SALES_DATABASE_URL=postgresql://read_user:password@database.example:5432/business
SOURCE_CRM_TOKEN=
SOURCE_API_ALLOWED_ORIGINS=https://api.example.com,https://crm.example.com
```

Use your actual read-only connection on the server. The example domain/account is illustrative. PostgreSQL connections use a read-only transaction and five-second connect/statement timeout. API origins are exact scheme/host/port entries, and redirects are refused. External API URLs require HTTPS; loopback HTTP is allowed for development. API reads have an eight-second timeout and 5 MB response limit.

Choose a saved reference and table/endpoint in the UI or API. Unknown config fields are rejected to prevent accidental credential persistence. For an API JSON array, `records_path` is empty; for nested `{data:{items:[...]}}`, use `data.items`. Imports cap records at 1–10,000 and do not automatically paginate or synchronize on a schedule. See [source connections](source-connections.md) for complete examples.

## Local embedding model

The embedding model is code-pinned rather than a freely selectable environment value:

- Name: `sentence-transformers/all-MiniLM-L6-v2`.
- Revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Dimension: 384, with normalized vectors.

`make model` downloads it explicitly. Normal API/worker loading uses `local_files_only=True` and `trust_remote_code=False`; retrieval fails if it is missing. Host and Compose caches are separate. Linux dependencies use CPU PyTorch 2.9.1. A different model requires compatible document/query identities; a different dimension also requires a vector schema/index migration.

## Frontend configuration

Fonts are bundled through Fontsource. The shader has reduced-motion/GPU fallbacks. Blume's virtual `blume:search-client` module resolves to the project catalog adapter in Vite, and React is deduplicated. Keep `frontend/.npmrc` and the npm lock together; they address Blume's documentation-runtime peer dependency resolution. Do not add `VITE_*` provider secrets: Vite-prefixed values are intended for browser delivery.
