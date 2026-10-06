# Scope and limitations

These are current implementation boundaries, not promised roadmap items.

| Area | Present behavior / boundary |
|---|---|
| Workspace and identity | One local workspace with synthetic author/reviewer/publisher identities. No production authentication, authorization, tenancy, or user audit identity. |
| Sources | Native PostgreSQL and HTTP GET readers, plus file uploads and registered locations. No native cloud/business-app connector, automatic pagination, schedule, webhook, or CDC. |
| Import size | Bounded local files/snapshots, UTF-8 structured inputs, supported RDF constructs. Not a bulk ingestion/data-lake pipeline. |
| Extraction | PDF/DOCX/text extraction is real. Scanned PDFs need external OCR. Unstructured graph facts use deterministic demo rules; structured records/RDF instances retain direct facts and evidence. |
| Semantics | Supported RDF classes/properties/labels/namespaces and selected SHACL constraints. No unrestricted OWL reasoning, remote SPARQL endpoint, or dedicated RDF triplestore. Unsupported constructs produce warnings rather than silently becoming supported. |
| Search | One pinned 384-dimensional local embedding model; vector/graph/hybrid modes. No learned reranker or universal embedding-provider selector. Saved retrieval cases are not a separate publication benchmark gate. |
| Governance | Revision generation, input fingerprints, current checks/reviews, and immutable manifests are implemented. Demo approval is a workflow check, not a production security boundary. |
| Chat | Real Claude Agent SDK → LiteLLM → OpenRouter/DeepSeek generation with scoped evidence and validated displays. Browser history and server packets are ephemeral. No durable archive, multi-process coordination, or edit/publish agent tools. |
| AI correctness | Citations and presentation validation constrain provenance/display. They do not guarantee that model conclusions or generated table values are correct. |
| Consumers | Application/product associations and active/pinned resolution are real; usage counters are labeled simulated. No credentials, actual traffic metering, or deployment into consumer apps. |
| Storage consistency | PostgreSQL owns visibility/activation; external writes can outlive rollback. No distributed transaction, automatic garbage collection, or retention policy. |
| Operations | Loopback Compose services and host/container runbooks. No deployed production host, TLS termination, secret manager, automatic backup/restore, or monitoring/alerting service. |
| API | Typed request models but many generic response schemas; no global idempotency header or API compatibility/versioning policy. See the API guide for actual stream/byte behavior. |
| Dependency footprint | Blume brings documentation/build dependencies. Chat is lazy-loaded; remaining lower-severity audit notices and chunk advisories are recorded in verification. Generated HTML, Mermaid, and math renderers are not enabled in chat. |
| Design references | Original design exports and alignment decisions are retained. Functional screens diverge from static references; no pixel-perfect fidelity claim. |

Production work would need explicit identity/authorization, trusted audit attribution, hardened transport/credential management, tenant boundaries, shared chat/run coordination, stronger extraction where required, coordinated backup/restore, and deployment-specific validation. Those changes should preserve revision/release evidence guarantees rather than bypassing them.
