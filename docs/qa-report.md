# Full QA and root-cause report

Date: October 6, 2026. This pass tests the implemented local product, not future production features. It combines real storage/model integration, live browser workflows, an independent business-code audit, deliberately failing regressions, actual Mermaid rendering, and container/fresh-install checks.

## Baseline and method

The baseline backend suite passed 64 tests. The baseline browser suite passed 13/14: dashboard loading exceeded its assertion deadline. A real browser Mermaid probe rendered three diagrams but failed the preparation sequence. Profiling the live workspace measured 511 SQL statements for 45 products and repeated snapshot/ontology reads.

New regressions were executed against the old behavior before fixes. The independent audit found additional concrete business defects; its initial backend regressions all failed, and the unbounded-rule browser regression showed an unintended maximum of one. Provider execution was not mocked for the separate live chat check; the regular browser chat tests still use a controlled external-generation seam.

## Reproduced causes and fixes

| Defect | Root cause | Fix and regression |
|---|---|---|
| Preparation diagram parse failure | A literal semicolon split a Mermaid sequence message into another statement. | Reworded the label; browser tests parse/render every tracked Markdown Mermaid block to nonempty SVG. |
| Slow dashboard / browser timeout | Per-product queries plus repeated evaluation/review snapshots created an N+1 workload. | Batched catalog inputs, retained request-local identity references, and memoized fingerprints per revision. Query-budget regression failed at 179 statements for 25 products. |
| Obsolete failure shown as current | Overview counted failed jobs for inactive source snapshots. | Restrict document failures to active evidence; regression excludes a superseded source job. |
| Overdue source count disagreed with freshness | Whole-day rounding and `>` delayed expiry until the following day. | Compare the exact synchronization timestamp plus freshness window; test expires a source by one second. |
| Malformed product settings persisted | Arbitrary config dictionaries reached code assuming mappings/numbers/model fields. | Validate finite quality thresholds, result limit, and complete embedding identity on creation/edit; rejected edits preserve generation. |
| Malformed search model caused 500 | `ModelRef(**dict)` received unchecked missing/invalid fields. | Typed model override schema rejects malformed input with 422. |
| Whitespace product name accepted on edit | Only the create schema checked nonblank names. | Apply the same trimmed-name validation to edits; original name remains on rejection. |
| Whitespace satisfied completeness | Raw nonempty strings counted as complete business metadata. | Trim text in evaluation snapshots; whitespace counts as missing, and fingerprints containing such outer whitespace become stale. |
| Concurrent publication/edit returned 500 | Publication locked Revision then Product; edits locked Product then Revision. | Both take Product before Revision, using non-key Product locks compatible with FK checks. Coordinated real-DB concurrency regression originally returned 201/500 and now requires 201/409. |
| Structured facts crashed with incomplete mappings | Imported field/relationship IRIs were indexed without confirming a property mapping. | Check used mappings before graph writes and return actionable 409; restoring mappings recovers CSV/JSON/Turtle builds. |
| Neighborhood/hybrid evidence selected wrong facts | Exact IDs were resolved through substring search, so row-1 could select row-10. | Exact Cypher lookup for roots/neighbors; fuzzy catalog search stays broad. Tests retain exact IDs, evidence, bounded neighbors, and missing-root404. |
| Word table knowledge disappeared | DOCX extraction read only top-level paragraphs. | Traverse body/table/nested-cell content in order, avoiding duplicate merged cells. New extraction records `extract-docx-v2/chunk-v1`; cached artifacts stay unchanged. |
| Editing a rule deleted siblings | Shape editing removed all attached property constraints. | Identify the original property path, update that constraint, preserve siblings, and reject ambiguous duplicate-path guided edits. |
| Approval diff hid constraint changes | Shape entries were indexed only by their shared NodeShape IRI. | Aggregate and compare every constraint per shape; first-constraint changes now appear. |
| Cleared definition links stayed present | Empty parent/domain/range values were ignored. | Explicit empty strings remove triples; omitted/null values preserve them. |
| RDFS classes changed kind silently | Kind protection considered OWL classes but omitted RDFS classes. | Preserve existing class kinds and reject conversion to object/datatype properties. |
| Invalid SHACL counts escaped as 500 | Cardinality inspection used unchecked integer conversion after persistence began. | Validate supported counts while parsing: nonnegative integers, one value per bound, minimum no greater than maximum; bad imports do not mutate the draft. |
| Unbounded rule gained maximum one | UI converted null maximum to one on selection. | Display/send null for unbounded maximum and retain it through a live edit/save. |
| Product screens skipped heading levels | Top guidance headings used h3 immediately after h1. | Use h2 for top guidance; full product-screen accessibility regression. |
| Prepared-stage labels lacked contrast | Stage-ready color ratio was 4.44:1 for small text. | Darker ready text preserves the design and passes WCAG AA checks. |

One newly written graph regression initially expected only two fuzzy matches despite its 19-record fixture. The fixture correctly matches row-1 and rows10–19; the assertion was corrected to preserve broad search while requiring exact neighborhood results. No production search behavior was weakened to satisfy it.

## Executed checks

| Check | Result |
|---|---|
| Expanded backend suite | **102/102 passed in63.57 seconds**, including the final whitespace-completeness regression. |
| Full browser suite | 21/21 passed in 1.4 minutes. |
| Mermaid rendering | All four diagrams parse and render with pinned Mermaid12.1.0 in Chromium; visible nonempty SVG, positive dimensions/labels, no syntax-error output/page errors. |
| Product-screen accessibility | All12 product destinations inspected at a published revision; no Axe violations, client errors, or observed API500 responses. |
| Connected application workflow | Register following active, change to pinned, reload, return to active; verify resolved release and cleared pinned ID. |
| Frontend build | TypeScript/Vite production build passed; generative chat stays lazy-loaded. |
| API/data references | Generated specification and dictionary refreshed; `make docs-check` passes. |
| Docker | API/worker images rebuilt; real storage probes, DOCX reading order, settings rejection, and gateway error sanitization pass. |
| Fresh install | Migrations001–010 applied to a blank temporary database;16 tables, HNSW/scope indexes, and revision-job uniqueness verified; temporary database removed. |
| Live performance | 51 products required12 SQL statements and0.333 seconds in the final profiled call, compared with511 statements for45 products before batching. |
| Live AI | Refreshed browser returned a real DeepSeek answer,30-day Fact, S1 citation, and expanded original evidence through Claude Agent SDK/LiteLLM/OpenRouter. |

The backend suite exercises real PostgreSQL/pgvector, MinIO, FalkorDB, pinned local embeddings, native PostgreSQL/API snapshots, processing/retry, RDF/SHACL, revision locking, review/publication, consumers, and scoped retrieval. Focused provider/SDK lifecycle tests use doubles only at network/runtime seams. The browser suite includes creation/reload, mixed imports, invalid import recovery, actual preparation/check/review/publication/search, context/correction scope, chat metadata isolation, image blocking, mobile, reduced motion, and GPU denial.

[Rendered preparation sequence](screenshots/preparation-sequence.png) and [live chat capture](screenshots/qa-live-chat.jpg) retain inspectable evidence. Mermaid API and GitHub fenced-diagram behavior were checked against [official Mermaid documentation](https://mermaid.js.org/config/usage.html) and [GitHub diagram documentation](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams).

## Scope and advisories

All reproduced defects listed above have fixes and regression coverage; this does not establish that every possible input or deployment is bug-free. Production identity, continuous connectors, durable/multi-process chat, OCR, unrestricted reasoning, and other documented gaps remain outside this implemented MVP.

The build still reports its existing deferred-chat chunk-size advisory and upstream Zod comment annotations. Nine lower-severity dependency audit notices remain in documentation/build dependencies; there are no high-severity findings in the checked installation. A fresh migration emits a harmless SQLAlchemy duplicate-metadata-copy warning while creating all tables/indexes correctly. These advisories are recorded rather than suppressed or addressed through unrelated breaking upgrades.
