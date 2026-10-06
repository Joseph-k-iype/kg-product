import { useState } from "react";
import { FileText, FileUp, Plus, RefreshCw, ArrowRight } from "lucide-react";
import { api, useData } from "../api/client";
import type { DocumentRecord, Source, Catalog, Job } from "../api/types";
import {
  Block,
  Field,
  Status,
  Empty,
  ErrorState,
  Loading,
  Drawer,
  EvidenceLink,
  useNotice,
  PageTitle,
  date,
} from "../components/shared";
import { scoped, useProduct } from "./product";
import { SourceFields, initialSource } from "./data-intake";
const stages = [
  ["uploaded", "Uploaded"],
  ["extracted", "Readable text"],
  ["chunked", "Excerpts"],
  ["embedded", "Search ready"],
  ["graph_built", "Facts ready"],
  ["validated", "Checks run"],
];
function Stages({ doc }: { doc: DocumentRecord }) {
  if (!doc.active)
    return <Status value="draft" label="Previous source snapshot" />;
  if (doc.data_kind === "definitions")
    return <Status value="ready" label="Concepts and rules imported" />;
  const stageIndex = stages.findIndex(([s]) => s === doc.state);
  return (
    <div className="stage-list">
      {stages.map(([key, label], i) => {
        const job = doc.jobs.find((j) => j.stage === key);
        return (
          <span
            key={key}
            className={
              "stage-item " +
              (job?.state === "failed"
                ? "failed"
                : i <= stageIndex
                  ? "ready"
                  : job?.state === "running"
                    ? "running"
                    : "")
            }
            title={job?.error || label}
          >
            {label}
            {i < stages.length - 1 && " →"}
          </span>
        );
      })}
    </div>
  );
}
export function DocumentsPage() {
  const { product, readonly } = useProduct();
  const path = scoped("documents");
  const { data, error, loading } = useData<DocumentRecord[]>(path, 3000);
  const [selected, setSelected] = useState<string | null>(null);
  const { busy, run } = useNotice();
  const upload = (files: File[]) =>
    run("Files imported", async () => {
      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        const d = await api<DocumentRecord>(path, "POST", form);
        setSelected(d.id);
      }
    });
  return (
    <>
      <Block
        title="Files & evidence"
        subtitle="Your original files stay connected to the facts and search results they support."
      >
        {!readonly && (
          <div className="block-body">
            <div className="upload-area">
              <FileUp color="var(--accent)" />
              <Field
                label="Upload files"
                hint="CSV, JSON, Turtle, PDF, Word, text or Markdown · up to 20 MB each"
              >
                <input
                  type="file"
                  multiple
                  disabled={busy}
                  accept=".csv,.json,.ttl,.turtle,.pdf,.docx,.txt,.md"
                  onChange={(e) => {
                    if (e.target.files?.length)
                      upload(Array.from(e.target.files));
                    e.target.value = "";
                  }}
                />
              </Field>
            </div>
          </div>
        )}
        {error && <ErrorState message={error} />}{" "}
        {loading ? (
          <Loading />
        ) : data?.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Uploaded</th>
                  <th>Preparation</th>
                  <th>Excerpts</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {data.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <button
                        style={{
                          border: 0,
                          background: "transparent",
                          padding: 0,
                          minHeight: 25,
                        }}
                        onClick={() => setSelected(d.id)}
                      >
                        <FileText size={16} />
                        {d.name}
                      </button>
                      <div className="subtext">
                        {(d.size / 1024).toFixed(1)} KB · {d.uploaded_by}
                        {d.data_kind === "definitions"
                          ? " · Definitions only"
                          : d.data_kind !== "document"
                            ? ` · ${d.record_count} imported records`
                            : ""}
                      </div>
                    </td>
                    <td>{date(d.uploaded_at)}</td>
                    <td>
                      <Status
                        value={
                          d.jobs.some((j) => j.state === "failed")
                            ? "failed"
                            : d.state
                        }
                      />
                    </td>
                    <td>{d.chunks.length}</td>
                    <td>
                      <EvidenceLink id={d.id} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="Add your first document"
            description="Start with a policy, guide, or support record. We will preserve the original and prepare readable evidence."
          />
        )}
      </Block>
      <div className="guidance">
        <h3>What happens after uploading?</h3>
        <p>
          Your document is stored, its text is read, and useful excerpts are
          prepared. Choose “Prepare knowledge” to make the evidence searchable
          and build supported demo facts.
        </p>
      </div>
      {selected && (
        <DocumentDrawer id={selected} onClose={() => setSelected(null)} />
      )}
    </>
  );
}
export function DocumentDrawer({
  id,
  onClose,
}: {
  id: string;
  onClose: () => void;
}) {
  const { data, error, loading } = useData<DocumentRecord>(
    "/documents/" + id,
    3000,
  );
  const { busy, run } = useNotice();
  const [view, setView] = useState("preview");
  return (
    <Drawer title={data?.name || "Document details"} onClose={onClose}>
      {error ? (
        <ErrorState message={error} />
      ) : loading ? (
        <Loading />
      ) : (
        data && (
          <>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <Status value={data.state} />
              <EvidenceLink id={id}>View original document</EvidenceLink>
            </div>
            <Stages doc={data} />
            <nav className="tabs" aria-label="Document detail views">
              {["preview", "excerpts", "preparation"].map((tab) => (
                <button
                  className={view === tab ? "active" : ""}
                  key={tab}
                  onClick={() => setView(tab)}
                >
                  {tab === "preview"
                    ? "Document"
                    : tab === "excerpts"
                      ? "Evidence excerpts"
                      : "Preparation history"}
                </button>
              ))}
            </nav>
            {view === "preview" && (
              <>
                <div className="document-preview">
                  {data.extracted_text ||
                    "Readable text will appear after the document is prepared."}
                </div>
                <dl className="detail-list">
                  <dt>Uploaded by</dt>
                  <dd>{data.uploaded_by}</dd>
                  <dt>Uploaded</dt>
                  <dd>{date(data.uploaded_at)}</dd>
                  <dt>Processing version</dt>
                  <dd>{data.processing_version}</dd>
                </dl>
              </>
            )}
            {view === "excerpts" &&
              (data.chunks.length ? (
                data.chunks.map((c) => (
                  <div className="evidence" key={c.id}>
                    <Status
                      value={c.embedded ? "ready" : "queued"}
                      label={
                        c.embedded
                          ? "Searchable"
                          : "Awaiting search preparation"
                      }
                    />
                    <blockquote>{c.text}</blockquote>
                    <small>
                      Characters {c.start}–{c.end}
                    </small>
                    <EvidenceLink id={data.id} />
                  </div>
                ))
              ) : (
                <Empty
                  title={
                    data.data_kind === "definitions"
                      ? "Definitions imported"
                      : "No excerpts yet"
                  }
                  description={
                    data.data_kind === "definitions"
                      ? "This file supplies concepts and rules. Add documents or records before preparing searchable evidence."
                      : "Prepare this file to create evidence excerpts."
                  }
                />
              ))}
            {view === "preparation" &&
              data.jobs.map((j) => (
                <div key={j.id} className="job-detail">
                  <div>
                    <h3>
                      {stages.find(([s]) => s === j.stage)?.[1] || j.stage}
                    </h3>
                    <p>
                      Attempt {j.attempt_count} · <Status value={j.state} />
                    </p>
                    {j.error && <p style={{ color: "#a93243" }}>{j.error}</p>}
                    <details>
                      <summary style={{ fontSize: 10 }}>
                        Attempt history
                      </summary>
                      {j.attempts.map((a) => (
                        <p key={a.number}>
                          Attempt {a.number}: {a.state} ·{" "}
                          {a.error || a.started_at}
                        </p>
                      ))}
                    </details>
                  </div>
                  {j.state === "failed" && (
                    <button
                      disabled={busy}
                      onClick={() =>
                        run("Retry queued", () =>
                          api("/jobs/" + j.id + "/retry", "POST"),
                        )
                      }
                    >
                      Retry failed stage
                    </button>
                  )}
                </div>
              ))}
            <details className="advanced">
              <summary>Advanced provenance</summary>
              <div>
                <dl className="detail-list">
                  <dt>Document ID</dt>
                  <dd>{data.id}</dd>
                  <dt>Version</dt>
                  <dd>{data.revision_id}</dd>
                  <dt>Storage object</dt>
                  <dd>{data.object_key}</dd>
                  <dt>Checksum</dt>
                  <dd>{data.sha256}</dd>
                </dl>
              </div>
            </details>
          </>
        )
      )}
    </Drawer>
  );
}
export function ProcessingPage() {
  const { product, readonly } = useProduct();
  const path = scoped("processing");
  const { data, error, loading } = useData<{
    documents: DocumentRecord[];
    revision_jobs: Job[];
  }>(path, 2000);
  const { busy, run } = useNotice();
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <>
      <Block
        title="Prepare knowledge"
        subtitle="Make documents readable and searchable, then check their supported facts."
        action={
          !readonly && (
            <button
              className="primary"
              disabled={busy}
              onClick={() =>
                run("Knowledge preparation queued", () =>
                  api(scopedOutside(product.id, path), "POST"),
                )
              }
            >
              <RefreshCw size={14} />
              Run preparation
            </button>
          )
        }
      >
        <div className="block-body guidance">
          Preparation makes imported records and document passages searchable.
          Structured records are imported directly; document fact extraction is
          fixture-backed in this demo. Retries keep successful work.
        </div>
        {error && <ErrorState message={error} />}{" "}
        {loading ? (
          <Loading />
        ) : data?.documents.length ? (
          data.documents.map((d) => (
            <div className="checklist-row" key={d.id}>
              <span className="round-icon">
                <FileText />
              </span>
              <div>
                <button
                  style={{
                    padding: 0,
                    border: 0,
                    background: "transparent",
                    minHeight: 20,
                  }}
                  onClick={() => setSelected(d.id)}
                >
                  {d.name}
                </button>
                <Stages doc={d} />
                <p>
                  {d.chunks.length} evidence excerpts ·{" "}
                  {d.chunks.filter((c) => c.embedded).length} searchable
                </p>
                {d.jobs
                  .filter((j) => j.state === "failed")
                  .map((j) => (
                    <div className="error" key={j.id}>
                      {j.error}
                      <button
                        disabled={busy}
                        style={{ marginLeft: 10 }}
                        onClick={() =>
                          run("Retry queued", () =>
                            api("/jobs/" + j.id + "/retry", "POST"),
                          )
                        }
                      >
                        Retry failed stage
                      </button>
                    </div>
                  ))}
              </div>
              <Status
                value={
                  d.jobs.some((j) => j.state === "failed") ? "failed" : d.state
                }
              />
            </div>
          ))
        ) : (
          <Empty
            title="Documents come first"
            description="Add a document, then run preparation."
          />
        )}
      </Block>
      {data?.revision_jobs?.length ? (
        <Block
          title="Fact preparation"
          subtitle="Revision-level processing, errors, and attempt history."
        >
          {data.revision_jobs.map((job) => (
            <div className="checklist-row" key={job.id}>
              <span className="round-icon">
                <RefreshCw />
              </span>
              <div>
                <h3>Prepare supported facts</h3>
                <p>
                  Attempt {job.attempt_count} · <Status value={job.state} />
                </p>
                {job.error && (
                  <div className="error" role="alert">
                    {job.error}
                  </div>
                )}
                <details>
                  <summary>Attempt history</summary>
                  {job.attempts.map((a) => (
                    <p key={a.number}>
                      Attempt {a.number}: {a.state} · {a.error || a.started_at}
                    </p>
                  ))}
                </details>
              </div>
              {job.state === "failed" && !readonly && (
                <button
                  disabled={busy}
                  onClick={() =>
                    run("Fact preparation retry queued", () =>
                      api("/jobs/" + job.id + "/retry", "POST"),
                    )
                  }
                >
                  Retry failed stage
                </button>
              )}
            </div>
          ))}
        </Block>
      ) : null}
      <div className="grid-3">
        <Block title="Readable documents">
          <div className="block-body">
            <h1>
              {data?.documents.filter((d) => d.extracted_text).length || 0}
            </h1>
            <p>Original files with readable text</p>
          </div>
        </Block>
        <Block title="Evidence excerpts">
          <div className="block-body">
            <h1>
              {data?.documents.reduce((n, d) => n + d.chunks.length, 0) || 0}
            </h1>
            <p>Passages linked to their source</p>
          </div>
        </Block>
        <Block title="Searchable excerpts">
          <div className="block-body">
            <h1>
              {data?.documents.reduce(
                (n, d) => n + d.chunks.filter((c) => c.embedded).length,
                0,
              ) || 0}
            </h1>
            <p>Ready for semantic search</p>
          </div>
        </Block>
      </div>
      {selected && (
        <DocumentDrawer id={selected} onClose={() => setSelected(null)} />
      )}
    </>
  );
}
function scopedOutside(id: string, path: string) {
  return path.replace("/processing?", "/processing/run?");
}
export function SourcesPage() {
  const { data, error, loading } = useData<Source[]>("/sources");
  const { data: catalog } = useData<Catalog>("/products");
  const [add, setAdd] = useState(false),
    [sourceDraft, setSourceDraft] = useState(initialSource),
    [sourcePreview, setSourcePreview] = useState<{
      name: string;
      record_count: number;
      message: string;
      columns: string[];
      sample_rows: Record<string, string>[];
    } | null>(null),
    [productId, setProduct] = useState(
      sessionStorage.getItem("currentProduct") || "",
    );
  const { busy, run } = useNotice();
  return (
    <>
      <PageTitle
        eyebrow="DOCUMENTS & SOURCES"
        title="Bring your knowledge together."
        description="Connect a database or API, or register any other source and import its exported files."
        action={
          <button className="primary" onClick={() => setAdd((v) => !v)}>
            <Plus size={15} />
            Add data source
          </button>
        }
      />
      {add && (
        <Block title="Register a source">
          <form
            className="block-body"
            onSubmit={(e) => {
              e.preventDefault();
              run("Source registered", async () => {
                await api("/sources", "POST", {
                  ...sourceDraft,
                  product_ids: productId ? [productId] : [],
                });
                setAdd(false);
                setSourceDraft(initialSource());
              });
            }}
          >
            <SourceFields value={sourceDraft} onChange={setSourceDraft} />
            <Field label="Associate product">
              <select
                value={productId}
                onChange={(e) => setProduct(e.target.value)}
              >
                <option value="">Associate later</option>
                {catalog?.items.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </Field>
            <div className="form-actions">
              <button type="button" onClick={() => setAdd(false)}>
                Cancel
              </button>
              <button className="primary" disabled={busy}>
                Save source
              </button>
            </div>
          </form>
        </Block>
      )}
      <div className="guidance">
        PostgreSQL and HTTP API sources can read actual records using a
        configured connection. Other locations are registered until a connector
        is configured; import CSV, Turtle, JSON, or document exports inside a
        product. “Demo sync” is available only on fixture sources and imports
        synthetic documents.
      </div>
      {sourcePreview && (
        <Block
          title={`Connection preview · ${sourcePreview.name}`}
          subtitle={`${sourcePreview.record_count} records · ${sourcePreview.message}`}
          action={
            <button onClick={() => setSourcePreview(null)}>
              Close preview
            </button>
          }
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {sourcePreview.columns.map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sourcePreview.sample_rows.map((row, i) => (
                  <tr key={i}>
                    {sourcePreview.columns.map((c) => (
                      <td key={c} className="text-wrap">
                        {row[c]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Block>
      )}
      <Block
        title="Source register"
        subtitle="Ownership, update targets, and connection state."
      >
        {error ? (
          <ErrorState message={error} />
        ) : loading ? (
          <Loading />
        ) : data?.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Owner</th>
                  <th>Connection</th>
                  <th>Update target</th>
                  <th>Last update</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {data.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <strong>{s.name}</strong>
                      <div className="subtext">
                        {s.location || "Local document upload"}
                      </div>
                    </td>
                    <td>{s.owner}</td>
                    <td>
                      <Status value={s.connection_state} />
                    </td>
                    <td>{s.freshness_days} days</td>
                    <td>
                      {s.last_synced_at
                        ? date(s.last_synced_at)
                        : "Not synchronized"}
                    </td>
                    <td>
                      {s.type === "postgres" || s.type === "api" ? (
                        <div className="source-actions">
                          <button
                            disabled={busy}
                            onClick={() =>
                              run("Connection checked", async () => {
                                const result = await api<
                                  Omit<
                                    NonNullable<typeof sourcePreview>,
                                    "name"
                                  >
                                >(`/sources/${s.id}/test`, "POST");
                                setSourcePreview({ ...result, name: s.name });
                              })
                            }
                          >
                            Test connection
                          </button>
                          <button
                            disabled={busy || !s.product_ids.length}
                            onClick={() =>
                              run("Source records imported", () =>
                                api(`/sources/${s.id}/sync`, "POST"),
                              )
                            }
                          >
                            Import snapshot
                          </button>
                        </div>
                      ) : s.type === "fixture" ? (
                        <button
                          disabled={busy || !s.product_ids.length}
                          onClick={() =>
                            run("Demo sync queued", () =>
                              api("/sources/" + s.id + "/sync-fixture", "POST"),
                            )
                          }
                        >
                          <RefreshCw size={13} />
                          Demo sync
                        </button>
                      ) : s.product_ids.length ? (
                        <a
                          className="button"
                          href={`/products/${s.product_ids[0]}/sources`}
                        >
                          Import exported files
                        </a>
                      ) : (
                        <span className="subtext">
                          Associate a product to import files
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="No sources registered"
            description="Start with a local document library or register an external location."
          />
        )}
      </Block>
    </>
  );
}
