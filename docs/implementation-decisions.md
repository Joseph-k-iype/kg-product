# Implementation decisions

These decisions were made during native execution.

- Ruling: make all product operations resolve an explicit revision ID when supplied, otherwise current draft; release retrieval explicitly resolves manifest — avoids ambiguous plan route examples — cost if wrong: API client adjustment.
- Ruling: split fast unit/service tests from real adapter integration tests while keeping all acceptance cases — plan's integration assertions mix fast and external tests — cost if wrong: extra test commands.
- Task 2 Ruling: fixture excerpt end offset is 63 (manual text count), not 60 in the initial test — corrected test literal — cost if wrong: incorrect citation boundary.
- Ruling: 12ui completed nine screen/HTML exports but prototype generation failed (holding composition lacks content area). Retain generated navigation markup/assets and design tokens; implement accessible responsive React layouts and real routes from exported page structures — cost if wrong: some target layout drift requiring comparison.
- Ruling: per-product consumer registrations represent app/product dependency associations — current UI registers one product per association — cost if wrong: additional multi-product grouping UI.
- Ruling: source-citation UI labels and stage copy use business terms, while the backend retains adapter terminology — requested user steering — cost if wrong: adjust copy only.
- Ruling: Linux torch uses the official CPU index, version 2.9.1 — local CPU MVP needs no CUDA stack — cost if wrong: retest the provider with another supported runtime version.
- Ruling: immutable MinIO originals remain during reset for recovery — deletes only metadata and exact graph namespace — cost if wrong: retained storage until explicit garbage collection.
- Final: Ruling: source expiry participates in evaluation fingerprints rather than changing revision content — freshness is a time-dependent gate — cost if wrong: reevaluation churn around expiration.
- Final: Ruling: deterministic graph IDs derive from scoped input fingerprints — retries reuse partial external artifacts across DB rollback — cost if wrong: bump extraction version when extraction behavior changes.

Deferred minor: expand impact previews with historical shape, evaluation, and release dependency references. Current previews preserve published data and show affected facts/mappings and required follow-up work.
