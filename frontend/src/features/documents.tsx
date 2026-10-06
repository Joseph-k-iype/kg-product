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
const stages = [
  ["uploaded", "Uploaded"],
  ["extracted", "Readable text"],
  ["chunked", "Excerpts"],
  ["embedded", "Search ready"],
  ["graph_built", "Facts ready"],
  ["validated", "Checks run"],
];
function Stages({ doc }: { doc: DocumentRecord }) {
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
  const upload = (file: File) =>
    run("Document uploaded", async () => {
      const form = new FormData();
      form.append("file", file);
      const d = await api<DocumentRecord>(path, "POST", form);
      setSelected(d.id);
    });
  return (
    <>
      <Block
        title="Documents & evidence"
        subtitle="Your original files stay connected to the facts and search results they support."
      >
        {!readonly && (
          <div className="block-body">
            <div className="upload-area">
              <FileUp color="#245887" />
              <Field
                label="Upload a document"
                hint="PDF, Word, text or Markdown · up to 20 MB"
              >
                <input
                  type="file"
                  disabled={busy}
                  accept=".pdf,.docx,.txt,.md"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) upload(file);
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
                  <th>Document</th>
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
                  title="No excerpts yet"
                  description="Prepare the document to create evidence excerpts."
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
          Preparation uses a local search model. Fact extraction is
          fixture-backed in this demo. Every stage records its result; retries
          keep successful work.
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
    [name, setName] = useState(""),
    [type, setType] = useState("local"),
    [owner, setOwner] = useState("Maya Chen"),
    [location, setLocation] = useState(""),
    [days, setDays] = useState(30),
    [productId, setProduct] = useState(
      sessionStorage.getItem("currentProduct") || "",
    );
  const { busy, run } = useNotice();
  return (
    <>
      <PageTitle
        eyebrow="DOCUMENTS & SOURCES"
        title="Start with trusted documents."
        description="Register where knowledge comes from, who owns it, and how often it needs updating."
        action={
          <button className="primary" onClick={() => setAdd((v) => !v)}>
            <Plus size={15} />
            Register source
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
                  name,
                  type,
                  owner,
                  location,
                  freshness_days: days,
                  product_ids: productId ? [productId] : [],
                });
                setAdd(false);
                setName("");
              });
            }}
          >
            <div className="form-grid">
              <Field label="Source name">
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field label="Source type">
                <select value={type} onChange={(e) => setType(e.target.value)}>
                  <option value="local">Local documents</option>
                  <option value="external">
                    External source — register only
                  </option>
                  <option value="fixture">Demo fixture source</option>
                </select>
              </Field>
              <Field label="Source owner">
                <input
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                />
              </Field>
              <Field label="Location">
                <input
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="Link or business system name"
                />
              </Field>
              <Field label="Update target in days">
                <input
                  type="number"
                  min={1}
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                />
              </Field>
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
            </div>
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
        External locations are registered, not live connections. “Demo sync”
        imports synthetic documents so you can try the workflow. Upload real
        local documents inside a product.
      </div>
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
