# Operations

This runbook covers the implemented local workspace. It does not define a production deployment, authentication scheme, multi-tenant policy, or managed backup service. See [configuration](configuration.md) for environment semantics and [troubleshooting](troubleshooting.md) for symptoms.

## Choose one API/worker runtime

| Mode | Storage | API/worker | Frontend | Embedding cache |
|---|---|---|---|---|
| Host development | Compose containers | `make api`, `make worker` | `make dev` | `backend/.model-cache` by default |
| Container runtime | Compose containers | `make up` | `make dev` separately | Compose `model-cache` volume at `/models` |

Do not run duplicate API/worker processes against the same demo workspace. Port 58000 is shared between the two API modes. Frontend production output is created by `make build`; this project does not provision a production static host or reverse proxy. A static host must route `/api` to FastAPI and support React route fallback.

## Host startup

```sh
cp .env.example .env          # only on a new installation; preserve existing values
chmod 600 .env
make install
make services
make migrate
make model
make seed
```

Start API, worker, and frontend in separate terminals using the README commands. `make seed` skips nonempty workspaces. Storage persists in named Docker volumes after processes stop.

## Container startup

```sh
make up
make dev
```

The API applies Alembic migrations before serving. Initialize the separate model volume with the download command in README before preparation/retrieval. The host seed script can populate the same storage once host dependencies/model are installed; do not start an additional host API/worker.

Use `docker compose logs --tail=100 api worker` for container process errors, `docker compose ps` for running services, and `docker compose stop api worker` to stop application containers while retaining storage. `docker compose down` retains named volumes by default; adding `--volumes` deletes them and is not routine shutdown.

## Health and diagnosis

```sh
curl --fail-with-body -sS http://127.0.0.1:58000/api/health
curl --fail-with-body -sS http://127.0.0.1:58000/api/chat/status
docker compose ps
docker compose logs --tail=50 postgres minio falkordb
```

Health returns three probes: PostgreSQL `SELECT 1`, MinIO bucket listing, and FalkorDB ping. It returns HTTP 200 even when a probe says `unavailable`; inspect each value. It does not test worker liveness, model cache readiness, chat credentials, or end-to-end preparation. Chat status reports whether required credentials are present, not whether the provider is reachable or funded.

Preparation status/attempts are visible in the UI and `/api/products/{id}/processing`. Start the worker if jobs stay queued. Failed jobs record an error and attempts; use the UI retry or `POST /api/jobs/{id}/retry` after resolving the cause. Expired running leases can be claimed again. Do not repeatedly retry an unreadable original; upload a readable corrected document instead.

## Database migrations

```sh
make migrate
cd backend
.venv/bin/alembic current
.venv/bin/alembic history
```

The current head is `010`. Apply migrations rather than creating ORM tables directly: indexes such as HNSW and revision-stage job uniqueness are migration-owned. Back up before changing schema. Historical migration files importing model definitions need special care when adding columns; the fresh-install chain must not create future columns twice.

## Coordinated backups

Releases reference SQL rows, MinIO objects, and FalkorDB builds. A SQL dump alone is insufficient for full recovery. Stop application writers and wait for active preparation/chat cleanup before taking a consistent local snapshot. In host mode stop the API/worker terminals; in container mode stop the API/worker containers. Keep storage services available for the database dump.

```sh
mkdir -p backups
chmod 700 backups
docker compose exec -T postgres pg_dump -U knowledge -d knowledge > backups/knowledge.sql
chmod 600 backups/knowledge.sql
docker volume inspect knowledge-product-manager_minio-data knowledge-product-manager_graph-data
```

Also archive/copy the **entire MinIO and FalkorDB named volumes** using your Docker host's volume-backup facility while their writers are stopped. Stop those containers during a physical volume copy. Preserve the matching SQL dump and volume archives as one dated snapshot. The model-cache volume is downloadable and can be recreated; preserving it shortens recovery. The default volume prefix comes from `name: knowledge-product-manager` in Compose; verify actual names if project naming was overridden.

Store private `.env` values separately using your normal secure secret backup. Keep dependency locks and the application commit ID with the backup. The `backups/` folder is ignored by Git. No automatic scheduled backup, remote replication, volume export script, retention, or encryption-at-rest policy is provided by this MVP.

## Restore

1. Stop API and worker writers and preserve the current state if needed.
2. Restore matching MinIO/FalkorDB volumes while those services are stopped, following your Docker host's volume restore procedure.
3. Start storage, then restore the SQL dump into an **empty** `knowledge` database with the intended local account. One local command is `docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U knowledge -d knowledge < backups/knowledge.sql` after explicitly preparing that empty database.
4. Restore server configuration privately, install dependencies, and run `make migrate` only with a compatible application version.
5. Restore/download the model cache, start one API/worker pair, and inspect all health values.
6. Verify an original document, a published retrieval/citation, a graph relationship, and a pinned consumer release before resuming edits.

The project does not provide an automatic cross-store restore command. A mismatched database/object/graph snapshot can fail integrity checks even if services are healthy.

## Local reset

`make reset` runs a guarded reset script with explicit confirmation built into the Makefile target. It is destructive to this local application's metadata and build namespace. It refuses arbitrary database names, does not delete infrastructure volumes, and retains immutable MinIO objects for recovery.

Stop API/worker first, take a backup, then:

```sh
make reset
make seed
```

Restart the processes afterward. This is a local demo reset, not a retention/garbage-collection workflow. Browser tests intentionally leave QA products; backend tests use the separate `knowledge_test` database. Never point these test/reset commands at a production system.

## Chat lifecycle and updates

The current request registry is in API memory. Run one API process for chat. Restart loses packet metadata/conversations; multiple processes require shared storage and coordinated reservation. Clearing a browser chat aborts the request, but SDK cleanup can take its documented grace period. No browser/server operation guarantees reversing provider billing.

After changing `.env`, restart the host API or recreate the container API. After changing code, rebuild containers. Keep Claude Agent SDK and LiteLLM pins deliberate: the gateway uses adapter internals to retain ownership of the underlying provider stream. Revalidate actual translation, tool execution, cancellation, and sanitized errors after upgrades.

## Verification commands

`make test` prepares a dedicated test DB and exercises real storage/model integration. `make test-e2e` requires live API/worker/frontend and uses synthetic workspace data. `make build` verifies TypeScript/production output. `make docs-check` verifies checked-in contract references without provider calls. Record executed results rather than copying historical counts into a new release claim.
