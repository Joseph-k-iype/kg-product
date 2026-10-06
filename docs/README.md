# Documentation index

Start with the [project README](../README.md) to run the application, or the [business user guide](user-guide.md) to use an existing workspace.

## System and contracts

- [Architecture](architecture.md): responsibilities, component and workflow diagrams, consistency, retrieval, and chat.
- [Data model](data-model.md): domain terms, relationships, snapshots, lifecycle, and migrations.
- [Generated database dictionary](reference/database.md): all 16 mapped tables and their columns.
- [API guide](api.md): revision scoping, request examples, response conventions, and agent streaming.
- [OpenAPI specification](api/openapi.json): exported OpenAPI 3.1 contract for the public endpoints.
- [Generated endpoint inventory](api/endpoints.md): all 56 declared operations and parameter/body references.
- [Adapter contracts](adapters.md): replacement seams and supported semantics.
- [Frontend strategy](frontend-strategy.md): React/Vite/TypeScript boundaries, data handling, and quality gates.
- [Chat design](chat-design.md): assistant-ui/Blume, Claude Agent SDK, and LiteLLM integration details.

## Setup and operation

- [Configuration](configuration.md): settings, secret references, ports, and working-directory assumptions.
- [Operations](operations.md): startup, health, migrations, backups, restore, worker recovery, and reset.
- [Troubleshooting](troubleshooting.md): symptoms and corrective actions.
- [Source connection setup](source-connections.md): native PostgreSQL/API snapshots.
- [Onboarding and imports](onboarding-imports.md): import semantics and readiness preferences.
- [Business user guide](user-guide.md): daily workflows in plain language.
- [Contributing](../CONTRIBUTING.md): development, verification, and documentation maintenance.
- [Scope and limitations](limitations.md): implemented behavior and production gaps.

## Evidence and historical decisions

- [Full QA and root-cause report](qa-report.md): reproduced defects, fixes, regression coverage, and final executed checks.

- [Verification record](verification.md): actual executed checks and known limits by implementation stage.
- [Implementation decisions](implementation-decisions.md): decisions and tradeoffs made during development.
- [Design notes](design.md) and [design spending](design-spend.md): retained reference provenance and constraints.
- [Chat documentation research](chat-ui-research.md): official documentation corpus inventory and review depth.
- [Initial specification](superpowers/specs/2026-10-06-knowledge-product-manager-design.md) and [initial plan](superpowers/plans/2026-10-06-knowledge-product-manager.md): historical scope before later onboarding/chat additions.

## Keep reference files current

Run `make docs` after changing routes, Pydantic request models, or ORM definitions. Run `make docs-check` before committing. The generator does not connect to infrastructure, retrieve business data, or call a model. The database dictionary comes from mapped metadata; migration-only indexes and logical references are explained separately in the data model guide.

Many API handlers return untyped dictionaries. The exported OpenAPI accurately reflects these declared schemas but leaves several responses generic and omits runtime error statuses. The API guide documents these gaps and actual wire behavior. Do not assume that a generated client validates every returned field or that an undocumented failure status cannot occur.
