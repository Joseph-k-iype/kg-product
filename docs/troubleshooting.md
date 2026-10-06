# Troubleshooting

| Symptom | Action |
|---|---|
| Cannot reach services | Run `docker compose ps`; start `make services`; inspect `docker compose logs --tail=50 postgres minio falkordb`. Check Operations in the app. |
| API schema/table error | Run `make migrate`. Containers apply Alembic migrations at API startup. |
| Preparation stays waiting | Start `make worker` or check the Compose worker container. PostgreSQL keeps queued jobs and attempts across restarts. |
| Corrupted PDF or textless scan | Inspect the failed Readable text stage. Upload a readable supported file; scanned PDFs require OCR outside this MVP. Retrying a permanently corrupted original will fail with another recorded attempt. |
| Search model unavailable | Run `make model` in the host runtime. For containers use the model-download command in README; the host and container caches are separate. Retry failed search-preparation jobs. |
| Concept changes block a release | Prepare current knowledge, rerun quality checks, then request a new review. Prior approvals cannot be reused across input changes. |
| Mapping error | Open Advanced representation settings; map all concepts, map existing properties with the correct kind, and use unique valid graph labels/keys. Guided edits generate defaults. |
| Publication fails | Keep using the previous release. Check the storage/graph error, restore the dependency, and retry publication. Activation occurs only after verification. |
| Source says Registered | A location/configuration was recorded but no snapshot was imported yet. For PostgreSQL/API sources, configure the server reference, test, and import; for other systems, upload an export. Demo sync is synthetic. |
| Browser port conflict | Use port 5174; do not stop an unrelated project on 5173. Set `API_URL` when starting Vite if the API uses another loopback port. |
| AI chat unavailable | Prepare the selected version; configure the server OpenRouter key and gateway token; restart/recreate the API. Chat status checks configuration presence only. |
| Missing chat cards after restart | Per-turn packets are retained in API memory. Restart/start a fresh conversation; durable archives and multi-process packet storage are not implemented. |
| npm install loops or fails | Use Node 22.12+ and the supplied frontend `.npmrc`/lock with `npm ci`; retain the Blume virtual module alias and React deduplication. |
| Documentation reference drift | Run `make docs`, review changes, then `make docs-check`. |
| Production deployment needed | The current identity selector is synthetic. Add real authentication, authorization, secrets management, and environment-specific operation controls before production use. |

Reset is explicit and restricted to the local `knowledge` database. Stop workers during reset, preserve a database/volume backup if needed, and restart with `make seed`. Test metadata is in `knowledge_test`; browser QA products stay in the live demo workspace by design.

See [operations](operations.md) for coordinated backups and [configuration](configuration.md) for environment and container addresses.
