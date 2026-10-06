# Generated PostgreSQL data dictionary

Generated from SQLAlchemy metadata with the PostgreSQL dialect. Run `make docs` to refresh.
See [data model](../data-model.md) for logical relationships, migration-only indexes, and lifecycle rules.
Defaults below are application or declared server defaults, not a dump of the live database.

## activity

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `revision_id` | `VARCHAR(36)` | yes | FK → revisions.id | — |
| `action` | `VARCHAR` | no | — | — |
| `actor` | `VARCHAR` | no | — | Demo author |
| `detail` | `JSON` | no | — | application callable: dict |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | no | — | application callable: now |

## chunks

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `revision_id` | `VARCHAR(36)` | no | FK → revisions.id | — |
| `document_id` | `VARCHAR(36)` | no | FK → documents.id | — |
| `ordinal` | `INTEGER` | no | — | — |
| `start` | `INTEGER` | no | — | — |
| `end` | `INTEGER` | no | — | — |
| `text` | `VARCHAR` | no | — | — |
| `processing_version` | `VARCHAR` | no | — | — |
| `embedding` | `VECTOR(384)` | yes | — | — |
| `model_name` | `VARCHAR` | yes | — | — |
| `model_revision` | `VARCHAR` | yes | — | — |
| `model_dimension` | `INTEGER` | yes | — | — |

Unique constraints: `document_id, ordinal, processing_version`.

## consumers

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `name` | `VARCHAR` | no | — | — |
| `type` | `VARCHAR` | no | — | — |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `release_policy` | `VARCHAR` | no | — | — |
| `release_id` | `VARCHAR(36)` | yes | FK → releases.id | — |
| `usage` | `JSON` | no | — | application callable: <lambda> |

## documents

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `revision_id` | `VARCHAR(36)` | no | FK → revisions.id | — |
| `source_id` | `VARCHAR(36)` | yes | FK → sources.id | — |
| `name` | `VARCHAR` | no | — | — |
| `data_kind` | `VARCHAR` | no | — | document |
| `structured_data` | `JSON` | no | — | application callable: dict |
| `active` | `BOOLEAN` | no | — | True |
| `content_type` | `VARCHAR` | no | — | — |
| `object_key` | `VARCHAR` | no | — | — |
| `sha256` | `VARCHAR(64)` | no | — | — |
| `size` | `INTEGER` | no | — | — |
| `extracted_key` | `VARCHAR` | yes | — | — |
| `extracted_sha256` | `VARCHAR` | yes | — | — |
| `extracted_text` | `VARCHAR` | yes | — | — |
| `state` | `VARCHAR` | no | — | uploaded |
| `prepare_requested` | `BOOLEAN` | no | — | False |
| `processing_version` | `VARCHAR` | no | — | extract-v1/chunk-v1 |
| `uploaded_by` | `VARCHAR` | no | — | Demo author |
| `uploaded_at` | `TIMESTAMP WITH TIME ZONE` | no | — | application callable: now |

## evaluation_cases

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `query` | `VARCHAR` | no | — | — |
| `expected_document_ids` | `JSON` | no | — | application callable: list |

## evaluations

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `revision_id` | `VARCHAR(36)` | no | FK → revisions.id | — |
| `generation` | `INTEGER` | no | — | — |
| `input_hash` | `VARCHAR` | no | — | — |
| `inputs` | `JSON` | no | — | — |
| `metrics` | `JSON` | no | — | — |
| `findings` | `JSON` | no | — | — |
| `state` | `VARCHAR` | no | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | no | — | application callable: now |

## fact_flags

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `revision_id` | `VARCHAR(36)` | no | FK → revisions.id | — |
| `build_id` | `VARCHAR(36)` | no | FK → graph_builds.id | — |
| `entity_id` | `VARCHAR` | no | — | — |
| `reason` | `VARCHAR` | no | — | — |
| `author` | `VARCHAR` | no | — | Demo author |
| `state` | `VARCHAR` | no | — | open |

## graph_builds

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `revision_id` | `VARCHAR(36)` | no | FK → revisions.id | — |
| `generation` | `INTEGER` | no | — | — |
| `ontology_id` | `VARCHAR(36)` | no | FK → ontologies.id | — |
| `mapping_id` | `VARCHAR(36)` | no | FK → mappings.id | — |
| `input_hash` | `VARCHAR` | no | — | — |
| `graph_key` | `VARCHAR` | no | — | — |
| `state` | `VARCHAR` | no | — | preparing |
| `instances` | `JSON` | no | — | application callable: list |
| `relationships` | `JSON` | no | — | application callable: list |
| `extraction_version` | `VARCHAR` | no | — | fixture-rules-v1 |

Unique constraints: `revision_id, input_hash`.

## jobs

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `revision_id` | `VARCHAR(36)` | no | FK → revisions.id | — |
| `document_id` | `VARCHAR(36)` | yes | FK → documents.id | — |
| `stage` | `VARCHAR` | no | — | — |
| `input_hash` | `VARCHAR` | no | — | — |
| `state` | `VARCHAR` | no | — | queued |
| `attempt_count` | `INTEGER` | no | — | 0 |
| `attempts` | `JSON` | no | — | application callable: list |
| `lease_until` | `TIMESTAMP WITH TIME ZONE` | yes | — | — |
| `worker_id` | `VARCHAR` | yes | — | — |
| `error` | `VARCHAR` | yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | no | — | application callable: now |

Unique constraints: `document_id, stage, input_hash`.

## mappings

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `revision_id` | `VARCHAR(36)` | no | FK → revisions.id | — |
| `ontology_id` | `VARCHAR(36)` | no | FK → ontologies.id | — |
| `version` | `INTEGER` | no | — | — |
| `definition` | `JSON` | no | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | no | — | application callable: now |

## ontologies

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `revision_id` | `VARCHAR(36)` | no | FK → revisions.id | — |
| `version` | `INTEGER` | no | — | — |
| `object_key` | `VARCHAR` | no | — | — |
| `sha256` | `VARCHAR(64)` | no | — | — |
| `unsupported` | `JSON` | no | — | application callable: list |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | no | — | application callable: now |

## products

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `name` | `VARCHAR(200)` | no | — | — |
| `purpose` | `VARCHAR` | no | — |  |
| `domain` | `VARCHAR(100)` | no | — | General |
| `owner` | `VARCHAR(200)` | no | — | Demo author |
| `tags` | `JSON` | no | — | application callable: list |
| `active_release_id` | `VARCHAR(36)` | yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | no | — | application callable: now |

## releases

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `revision_id` | `VARCHAR(36)` | no | FK → revisions.id | — |
| `number` | `INTEGER` | no | — | — |
| `manifest` | `JSON` | no | — | — |
| `object_key` | `VARCHAR` | no | — | — |
| `sha256` | `VARCHAR` | no | — | — |
| `published_by` | `VARCHAR` | no | — | demo-publisher |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | no | — | application callable: now |

Unique constraints: `product_id, number`; `revision_id`.

## reviews

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `revision_id` | `VARCHAR(36)` | no | FK → revisions.id | — |
| `generation` | `INTEGER` | no | — | — |
| `evaluation_id` | `VARCHAR(36)` | no | FK → evaluations.id | — |
| `input_hash` | `VARCHAR` | no | — | — |
| `summary` | `VARCHAR` | no | — | — |
| `requester` | `VARCHAR` | no | — | demo-author |
| `reviewer_id` | `VARCHAR` | yes | — | — |
| `decision_reason` | `VARCHAR` | yes | — | — |
| `state` | `VARCHAR` | no | — | submitted |
| `changes` | `JSON` | no | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | no | — | application callable: now |

## revisions

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `product_id` | `VARCHAR(36)` | no | FK → products.id | — |
| `number` | `INTEGER` | no | — | — |
| `generation` | `INTEGER` | no | — | 1 |
| `state` | `VARCHAR(30)` | no | — | draft |
| `config` | `JSON` | no | — | application callable: dict |
| `ontology_id` | `VARCHAR(36)` | yes | — | — |
| `mapping_id` | `VARCHAR(36)` | yes | — | — |
| `graph_build_id` | `VARCHAR(36)` | yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | no | — | application callable: now |

## sources

| Column | PostgreSQL type | Nullable | Key/reference | Default |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | no | PK | application callable: uid |
| `name` | `VARCHAR` | no | — | — |
| `type` | `VARCHAR` | no | — | local |
| `owner` | `VARCHAR` | no | — | — |
| `location` | `VARCHAR` | no | — |  |
| `config` | `JSON` | no | — | application callable: dict |
| `freshness_days` | `INTEGER` | no | — | 30 |
| `product_ids` | `JSON` | no | — | application callable: list |
| `connection_state` | `VARCHAR` | no | — | registered |
| `last_synced_at` | `TIMESTAMP WITH TIME ZONE` | yes | — | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | no | — | application callable: now |
