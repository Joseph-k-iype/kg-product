# Live source setup

Business users can choose a PostgreSQL database or HTTP API in onboarding or Documents & Sources. An administrator provides a saved connection reference. Add actual values to the ignored root `.env` or process environment; source records store names such as `SOURCE_SALES_DATABASE_URL`, never the connection password/token. References must begin with `SOURCE_`.

## PostgreSQL

```dotenv
SOURCE_SALES_DATABASE_URL=postgresql://read_user:password@database.example:5432/business
```

Use a database account with SELECT permission only on the intended tables. Choose that connection name, the schema (usually public), a table, and a record cap in the UI. The connector quotes identifiers, reads SELECT only, opens a read-only transaction, applies a five-second connection/statement timeout, and retains a CSV snapshot as original evidence. Empty tables produce an actionable no-records message. Preview reports whether the cap truncated the snapshot.

## HTTP APIs

```dotenv
SOURCE_API_ALLOWED_ORIGINS=https://api.example.com,https://crm.example.com
SOURCE_CRM_TOKEN=the-api-bearer-token
```

Enter a GET endpoint, choose JSON/CSV, and optionally use SOURCE_CRM_TOKEN as the saved credential. For a JSON array leave “Records inside the response” empty; for an object containing `{ data: { items: [...] } }`, use `data.items`. Objects nested inside fields are preserved as JSON text. The complete original response is stored, while selected records become separate evidence excerpts.

Origins are exact scheme/host/port entries. External endpoints require HTTPS; HTTP is permitted for loopback development origins only. Redirects are refused rather than forwarding credentials elsewhere. Responses are bounded to 5 MB and eight seconds. Pagination is not automatic: use a suitably scoped endpoint; preview states when the chosen record cap truncates imported data.

Choose **Test connection**, then **Import snapshot**, or select import during draft creation. Changed snapshots replace current draft source data without modifying a published release. Older originals remain available for inspection. Repeated imports of the same original and normalized record selection are idempotent.

Host processes read `.env` on each connector operation. API containers load `.env` through Compose and require recreation after environment changes. Explicit infrastructure URLs from Compose override the local-host infrastructure values. A database running on your Mac needs a container-reachable address (for example `host.docker.internal`) when called from the container. No real external source credentials were supplied or used during implementation.

Cloud storage, business applications, websites, and other locations can be registered now and imported through their exports. Only PostgreSQL and HTTP APIs have native live readers in this version.
