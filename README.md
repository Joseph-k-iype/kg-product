# Knowledge Product Manager

A local business application for creating, preparing, checking, approving, publishing, and searching governed knowledge products. The interface uses simple business language, a modern grid of flat blocks, and evidence-first workflows. Technical concepts, RDF source, and mappings live in Advanced views.

## Run locally

Requires Docker Compose, Node.js 20+, and uv. The pinned Python runtime is 3.12. Local demo ports are bound to loopback.

```sh
cp .env.example .env
make install
make services
make migrate
make model
make seed
```

Start each long-running process in a separate terminal:

```sh
make api
make worker
make dev
```

Open [the application](http://127.0.0.1:5174/overview). The API and its interactive schema are at [localhost:58000/docs](http://127.0.0.1:58000/docs). PostgreSQL uses port 55432, MinIO 59000 (console 59001), and FalkorDB 56379. Port 5174 avoids interfering with other Vite applications.

The first model download needs network access. `make model` downloads the pinned all-MiniLM-L6-v2 revision. Normal preparation and retrieval use the local cache; there is no lexical-search substitution if that model is missing. The first search in a fresh API process can take longer while the model loads.

## Business workflow

1. Create a product in the five-step guided flow. An incomplete draft is allowed.
2. Preview and import CSV, JSON records, Turtle, PDF, Word, text, or Markdown files. You can mix formats or configure a PostgreSQL/API source during onboarding.
3. Choose a concept starter or use business forms to describe concepts, attributes, relationships, and rules.
4. Run preparation. The worker records attempts, errors, and safe retries.
5. Run quality checks and resolve findings. Each of seven dimensions has its own measured value and threshold.
6. Enter a change summary and request approval. Select the synthetic Demo reviewer identity in the header to approve or request changes.
7. Publish the approved revision. The prior release remains active if artifact preparation fails.
8. Search a published release or a labeled draft preview; open the source evidence. Register applications that follow the active release or pin a specific release.

The seed includes HR Policies, Payments, Customer Complaints, and Application Estate in different readiness states. Original documents and local-model vectors are real stored artifacts. Structured records and Turtle relationships are imported directly with source evidence. Document fact extraction is intentionally fixture-backed; each fact exposes its processing version and source excerpts. Consumer usage is simulated and labeled. Identities are synthetic, and production authentication/authorization is not implemented.

## Container runtime

`make up` starts the same infrastructure plus API and worker containers. The frontend still runs with `make dev`. Do not run the host API/worker and container API/worker simultaneously. The model cache in containers is separate from the host cache; initialize it before using retrieval:

```sh
docker compose exec api python -c "from sentence_transformers import SentenceTransformer; from app.adapters.embeddings import MODEL_NAME,MODEL_REVISION; SentenceTransformer(MODEL_NAME,revision=MODEL_REVISION,cache_folder='/models',trust_remote_code=False)"
```

For the demo seed, run host `make seed` against the loopback services after `make install`, `make migrate`, and `make model`. The seed skips nonempty workspaces. Database migrations run automatically at container API startup. Dependency locks are supplied for both runtimes.

## Verification

```sh
make test                 # real services + real model; creates knowledge_test
make test-fast            # omit the actual-model journey (services still needed)
make test-e2e             # live API/worker/frontend; creates synthetic QA products
make build                # TypeScript and production frontend build
```

Backend tests isolate metadata in `knowledge_test`. Browser tests use the running demo workspace and leave products named `Browser product …` and `Journey …` so you can inspect their saved results. See [verification report](docs/verification.md) for executed results, scope, and limits. Synthetic text, PDF, DOCX, and ontology fixtures are under `fixtures/`.

## Reset and recovery

Back up local metadata before resetting:

```sh
docker compose exec -T postgres pg_dump -U knowledge knowledge > knowledge-backup.sql
```

Stop API and worker processes, run `make reset`, then `make seed`, and restart them. Reset clears only the local application's metadata and exact FalkorDB build namespace; immutable MinIO originals remain available for recovery. It refuses other database names and does not delete infrastructure volumes. To preserve a snapshot, keep the SQL backup and the Docker volumes together; releases refer to objects and builds across all three services.

## Architecture

PostgreSQL owns products, revisions, jobs, evaluations, decisions, consumer associations, and activity. pgvector stores 384-dimensional excerpt vectors. MinIO stores original documents, extracted text, versioned canonical Turtle, and immutable release manifests. RDFLib and pySHACL parse, inspect, and validate supported definitions; there is no RDF triplestore or remote SPARQL endpoint. FalkorDB owns build-scoped instance graphs with explicit versioned vocabulary mappings.

A release prepares and verifies immutable artifacts before activating a manifest in one PostgreSQL transaction. Queries resolve that manifest's exact evidence snapshot and graph build. A published version is read-only; a new draft copies its document/chunk snapshot and requires current preparation, checks, and review.

[Adapter contracts](docs/adapters.md) and [troubleshooting](docs/troubleshooting.md) describe implementation seams and failure recovery. The [approved specification](docs/superpowers/specs/2026-10-06-knowledge-product-manager-design.md) and [implementation plan](docs/superpowers/plans/2026-10-06-knowledge-product-manager.md) record the scope. WeKnora's document-first onboarding, processing timeline, cited search, and modularity informed the experience; no WeKnora source code was copied. See [WeKnora](https://github.com/Tencent/WeKnora).

## Bring business data into a product

Onboarding now has a **Bring data** step. Mix documents, CSV or JSON records, and Turtle files in one draft. Files are previewed before creation: CSV/JSON shows fields and sample records; Turtle reports concepts, relationships, and whether it contains only definitions. Invalid imports can be removed without losing setup. Up to 20 files, 20 MB each, and 100 MB total are accepted per draft. Structured text must be UTF-8; CSV/JSON records are bounded to 10,000 records and 100 fields. Turtle uses the supported RDF/SHACL vocabulary and is bounded to 2 MB/50,000 statements.

The **Readiness** step sets preferences; it does not evaluate the product yet. “How many matching results?” controls the maximum evidence matches per search. The options explain their count, and actual quality checks run after preparation. Creation commits the product, associated source, and imports together. A validation/source failure does not leave a partially created product.

**PostgreSQL and HTTP API connections** can read actual data. Configure server connection references as described in [source setup](docs/source-connections.md), choose a table or endpoint, test/preview, then import a read-only snapshot. Other systems can be registered by location and brought in through file exports. An API origin must be explicitly approved; credentials stay in server environment/.env configuration and are not returned in source metadata.

Refreshing a source supersedes its previous snapshot only in the editable draft. Originals and earlier published releases remain intact. Superseded snapshots are excluded from preparation, draft facts, embeddings/search, quality checks, and subsequent releases. Identical snapshots are reused. These are manual snapshot imports; there is no background schedule or automatic API pagination.
