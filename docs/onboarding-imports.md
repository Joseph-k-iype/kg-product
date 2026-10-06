# Onboarding and data import changes

User request: explain the readiness counter; let users bring structured CSV/Turtle, unstructured documents, and data sources. Live source priority: databases and APIs. The existing light/red Inter/Geist design remains in use. 12ui generation stopped before buying new candidates because its allowance/wallet was exhausted; the existing approved design system was extended without requiring a top-up.

Implemented: five-step setup with Bring data; multi-file previews/removal; explanatory search-result presets and quality timing; atomic creation; native CSV/JSON records, Turtle records/relationships/definitions; original-file evidence; draft-scoped automatic definitions/mappings; source configuration and test/import actions; PostgreSQL and HTTP API readers; generic registered-location/file-export fallback. Migrations009 and010 add normalized records/configuration and current snapshot state.

A fresh reviewer identified four Important data-fidelity issues. Each was reproduced by a failing regression and fixed: changed source snapshots no longer retain outdated draft records; Turtle labels/comments/language/typed values reach quality validation; blank-node identities are scoped to the imported document and retained on draft cloning; inferred declarations reuse existing vocabulary kinds/labels. Named Turtle identifiers can merge across files; anonymous identifiers cannot. No second reviewer was dispatched.

The previous source snapshot stays inspectable and its original remains immutable. Inactive chunks are filtered consistently from processing, graph builds, evaluation snapshots, retrieval, and future releases. Old published manifests continue to resolve the exact original graph/chunks. Pending work for superseded source data is retired.

Limits: supported file formats only; no OCR for scanned documents; no unrestricted reasoning; PostgreSQL is the first database reader; HTTP readers support GET, JSON/CSV, and optional bearer references only. Other systems are registered rather than falsely represented as connected. Source refresh and pagination are manual; production authentication remains outside the local MVP.
