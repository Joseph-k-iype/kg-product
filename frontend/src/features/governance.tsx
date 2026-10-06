import { useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, Play, Send, Check, Clock } from "lucide-react";
import { api, useData } from "../api/client";
import type { Evaluation, Review, Release, Metric } from "../api/types";
import {
  Block,
  Field,
  Status,
  Empty,
  ErrorState,
  Loading,
  Drawer,
  useNotice,
  date,
  NextLink,
} from "../components/shared";
import { scoped, useProduct } from "./product";
function QualityRows({
  metrics,
  previous,
}: {
  metrics: Metric[];
  previous?: Metric[];
}) {
  return (
    <>
      {metrics.map((m, i) => (
        <div className="metric-row" key={m.key}>
          <span className="step-number">{i + 1}</span>
          <div>
            <strong>{m.label}</strong>
            <p style={{ fontSize: 10 }}>
              Required: {Math.round(m.threshold * 100)}%
              {previous &&
                " · Previously " +
                  (previous.find((p) => p.key === m.key)?.value === null
                    ? "not measured"
                    : Math.round(
                        (previous.find((p) => p.key === m.key)?.value || 0) *
                          100,
                      ) + "%")}
            </p>
          </div>
          <span style={{ fontSize: 12 }}>
            {m.value === null
              ? "Not measured"
              : Math.round(m.value * 100) + "%"}
          </span>
          <Status value={m.state} />
        </div>
      ))}
    </>
  );
}
export function HealthPage() {
  const { product, readonly } = useProduct();
  const path = scoped("evaluations");
  const { data, error, loading } = useData<Evaluation[]>(path);
  const { busy, run } = useNotice();
  const latest = data?.[0];
  return (
    <>
      <div className="grid-2">
        <Block
          title="Knowledge quality checks"
          subtitle="Each dimension is measured separately against its requirements."
          action={
            !readonly && (
              <button
                className="primary"
                disabled={busy}
                onClick={() =>
                  run("Quality checks completed", () => api(path, "POST"))
                }
              >
                <Play size={13} />
                Run checks
              </button>
            )
          }
        >
          {error ? (
            <ErrorState message={error} />
          ) : loading ? (
            <Loading />
          ) : latest ? (
            <QualityRows
              metrics={latest.metrics}
              previous={data?.[1]?.metrics}
            />
          ) : (
            <Empty
              title="See how ready your knowledge is"
              description="Run checks after preparing documents and concepts. Missing evidence will show as insufficient data."
            />
          )}
        </Block>
        <div>
          <Block title="Readiness for publication">
            <div className="block-body">
              <Status value={latest?.state || "not_checked"} />
              <p style={{ fontSize: 12, marginTop: 16 }}>
                {latest?.state === "passed"
                  ? "All required checks passed for the current inputs. Request reviewer approval next."
                  : latest?.state === "stale"
                    ? "This draft changed after the last check. Run checks again before requesting approval."
                    : "Resolve findings and supply missing inputs before requesting approval."}
              </p>
              <p style={{ fontSize: 10, marginTop: 12 }}>
                {latest
                  ? "Last run: " + date(latest.created_at)
                  : "No checks have run yet."}
              </p>
              <div style={{ marginTop: 20 }}>
                <NextLink to={"/products/" + product.id + "/reviews"}>
                  Go to approvals
                </NextLink>
              </div>
            </div>
          </Block>
          <div className="guidance">
            A check stays current only while its documents, concepts,
            preparation, and settings stay the same.
          </div>
        </div>
      </div>
      {latest && (
        <Block
          title="Findings"
          subtitle="Each issue links to the place where it can be resolved."
        >
          {latest.findings.length ? (
            latest.findings.map((f, i) => (
              <div className="checklist-row" key={i}>
                <span className="round-icon">
                  <ShieldCheck />
                </span>
                <div>
                  <h3>{f.message}</h3>
                  {f.entity_id && (
                    <p>Affected fact: {f.entity_id.split("/").pop()}</p>
                  )}
                </div>
                <Link
                  className="button"
                  to={f.url || "/products/" + product.id + "/health"}
                >
                  Resolve
                </Link>
              </div>
            ))
          ) : (
            <div className="block-body">
              <p>
                <Check size={15} /> No findings for this run.
              </p>
            </div>
          )}
        </Block>
      )}
      {data && data.length > 1 && (
        <Block title="Evaluation history">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Date</th>
                  <th>Input generation</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={r.id}>
                    <td>{i === 0 ? "Latest run" : "Previous run"}</td>
                    <td>{date(r.created_at)}</td>
                    <td>{r.generation}</td>
                    <td>
                      <Status value={r.state} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Block>
      )}
    </>
  );
}
export function ReviewsPage() {
  const { product, readonly } = useProduct();
  const path = "/reviews?product_id=" + product.id;
  const { data, error, loading } = useData<Review[]>(path);
  const { data: checks } = useData<Evaluation[]>(scoped("evaluations"));
  const { data: releases } = useData<Release[]>(
    "/products/" + product.id + "/releases",
  );
  const [summary, setSummary] = useState(""),
    [selected, setSelected] = useState<Review | null>(null),
    [reason, setReason] = useState("");
  const { busy, run } = useNotice();
  const active = data?.find((r) => r.state === "approved");
  const reviewer = sessionStorage.getItem("identity") === "Demo reviewer";
  const choose = (r: Review) => {
    setSelected(r);
    setReason("");
  };
  return (
    <>
      <div className="grid-2">
        <Block
          title="Approval requests"
          subtitle="Review the changes, quality evidence, and impact before publication."
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
                    <th>Change summary</th>
                    <th>Requested by</th>
                    <th>Status</th>
                    <th>Review</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((r) => (
                    <tr key={r.id}>
                      <td className="text-wrap">
                        <strong>{r.summary}</strong>
                        <div className="subtext">{date(r.created_at)}</div>
                      </td>
                      <td>
                        {r.requester === "demo-author"
                          ? "Demo author"
                          : r.requester}
                      </td>
                      <td>
                        <Status value={r.state} />
                      </td>
                      <td>
                        <button onClick={() => choose(r)}>
                          Review changes
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              title="No approval requests yet"
              description="Run current quality checks, then enter a summary and request approval."
            />
          )}
        </Block>
        <div>
          {!readonly && (
            <Block title="Request a review">
              <form
                className="block-body"
                onSubmit={(e) => {
                  e.preventDefault();
                  run("Approval requested", () =>
                    api("/products/" + product.id + "/reviews", "POST", {
                      summary,
                    }),
                  );
                }}
              >
                <Field label="Change summary">
                  <textarea
                    required
                    value={summary}
                    onChange={(e) => setSummary(e.target.value)}
                    placeholder="What changed, and why is it ready to use?"
                  />
                </Field>
                <p className="content-note">
                  Current passing checks are required.{" "}
                  {checks?.[0]?.state === "passed"
                    ? "Current checks have passed."
                    : "Run quality checks before submitting."}
                </p>
                <button
                  className="primary"
                  disabled={
                    busy || checks?.[0]?.state !== "passed" || !summary.trim()
                  }
                >
                  <Send size={14} />
                  Request approval
                </button>
              </form>
            </Block>
          )}
          <Block title="Publish a release">
            <div className="block-body">
              <p style={{ fontSize: 12, marginBottom: 18 }}>
                Publication verifies all referenced evidence, prepares an
                immutable release, and makes it available to connected apps.
              </p>
              <button
                className="primary"
                disabled={
                  busy || readonly || !active || checks?.[0]?.state !== "passed"
                }
                onClick={() =>
                  run("Release published", () =>
                    api("/products/" + product.id + "/releases", "POST"),
                  )
                }
              >
                Publish
              </button>
              <p className="content-note">
                {readonly
                  ? "This version is already published."
                  : active
                    ? "Current reviewer approval recorded."
                    : "Reviewer approval is required."}
              </p>
            </div>
          </Block>
        </div>
      </div>
      {selected && (
        <Drawer
          title="Review knowledge changes"
          onClose={() => setSelected(null)}
        >
          <Status
            value={
              data?.find((r) => r.id === selected.id)?.state || selected.state
            }
          />
          <h3 style={{ margin: "20px 0 8px" }}>{selected.summary}</h3>
          <p>Requester: Demo author · {date(selected.created_at)}</p>
          <h3 style={{ marginTop: 24 }}>Before and after</h3>
          <div className="review-diff">
            <div>
              <h3>Published release</h3>
              <p>
                {selected.changes.before
                  ? "Existing published knowledge"
                  : "First publication"}
              </p>
              <p>
                {JSON.stringify(
                  selected.changes.before?.metadata || {},
                  null,
                  2,
                )}
              </p>
              <p>
                {Array.isArray(selected.changes.before?.documents)
                  ? selected.changes.before.documents.length
                  : 0}{" "}
                documents
              </p>
            </div>
            <div>
              <h3>Proposed revision</h3>
              <p>
                {JSON.stringify(selected.changes.after.metadata || {}, null, 2)}
              </p>
              <p>
                {Array.isArray(selected.changes.after.documents)
                  ? selected.changes.after.documents.length
                  : 0}{" "}
                documents
              </p>
              <p>
                Concept and representation versions are captured with this
                request.
              </p>
            </div>
          </div>
          <h3>Business definition changes</h3>
          <div className="evidence">
            {selected.changes.ontology_diff?.added.map((d) => (
              <p key={d.iri}>Added: {d.label}</p>
            ))}
            {selected.changes.ontology_diff?.removed.map((d) => (
              <p key={d.iri}>Removed: {d.label}</p>
            ))}
            {selected.changes.ontology_diff?.changed.map((d, i) => (
              <p key={i}>
                Changed: {d.before.label} → {d.after.label}
              </p>
            ))}
            {!selected.changes.ontology_diff && (
              <p>Version details captured in the original request.</p>
            )}
          </div>
          <h3>Documents in this change</h3>
          <div className="evidence">
            <p>
              Previously:{" "}
              {selected.changes.document_changes?.before.join(", ") ||
                "No published documents"}
            </p>
            <p>
              Proposed:{" "}
              {selected.changes.document_changes?.after.join(", ") ||
                "See captured version details"}
            </p>
          </div>
          <h3>Quality evidence</h3>
          <QualityRows metrics={selected.changes.quality_evidence} />
          <div className="guidance" style={{ marginTop: 20 }}>
            Connected apps following the active release will receive the new
            version after publication. Apps pinned to a release stay on that
            version.
          </div>
          {selected.state === "submitted" && (
            <>
              <p className="content-note">
                {reviewer
                  ? "You are using the synthetic reviewer identity."
                  : "Choose “Demo reviewer” in the header to make a review decision."}
              </p>
              <Field
                label="Decision reason"
                hint="Required when requesting changes."
              >
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </Field>
              <div className="form-actions">
                <button
                  disabled={busy || !reviewer || !reason.trim()}
                  onClick={() =>
                    run("Changes requested", async () => {
                      await api(
                        "/reviews/" + selected.id + "/decision",
                        "POST",
                        {
                          decision: "reject",
                          reason,
                          reviewer_id: "demo-reviewer",
                        },
                      );
                      setSelected(null);
                    })
                  }
                >
                  Request changes
                </button>
                <button
                  className="primary"
                  disabled={busy || !reviewer}
                  onClick={() =>
                    run("Revision approved", async () => {
                      await api(
                        "/reviews/" + selected.id + "/decision",
                        "POST",
                        {
                          decision: "approve",
                          reason,
                          reviewer_id: "demo-reviewer",
                        },
                      );
                      setSelected(null);
                    })
                  }
                >
                  Approve revision
                </button>
              </div>
            </>
          )}
          {selected.decision_reason && (
            <p>Decision reason: {selected.decision_reason}</p>
          )}
          <details className="advanced" style={{ marginTop: 20 }}>
            <summary>Advanced — exact captured version changes</summary>
            <div>
              <pre
                style={{
                  fontSize: 10,
                  whiteSpace: "pre-wrap",
                  overflowWrap: "anywhere",
                }}
              >
                {JSON.stringify(selected.changes, null, 2)}
              </pre>
            </div>
          </details>
        </Drawer>
      )}
    </>
  );
}
export function ReleasesPage() {
  const { product } = useProduct();
  const {
    data: releases,
    error,
    loading,
  } = useData<Release[]>("/products/" + product.id + "/releases");
  const { data: activity } = useData<
    { id: string; action: string; actor: string; created_at: string }[]
  >("/products/" + product.id + "/activity");
  const [selected, setSelected] = useState<Release | null>(null);
  return (
    <div className="grid-2">
      <Block
        title="Published releases"
        subtitle="Each release pins a consistent set of documents, concepts, facts, and search settings."
      >
        {error ? (
          <ErrorState message={error} />
        ) : loading ? (
          <Loading />
        ) : releases?.length ? (
          releases.map((r) => (
            <div className="publication-row" key={r.id}>
              <div>
                <h3>Release {r.number}</h3>
                <p>{date(r.created_at)} · Demo publisher</p>
              </div>
              <Status
                value={
                  r.id === product.active_release_id ? "active" : "published"
                }
                label={
                  r.id === product.active_release_id
                    ? "Active release"
                    : "Previous release"
                }
              />
              <button onClick={() => setSelected(r)}>Inspect</button>
            </div>
          ))
        ) : (
          <Empty
            title="No published releases"
            description="Prepare, check, and approve a draft to publish your first release."
          />
        )}
      </Block>
      <Block title="Activity history">
        {activity?.map((a) => (
          <div className="publication-row" key={a.id}>
            <span className="round-icon">
              <Clock size={15} />
            </span>
            <div style={{ flex: 1 }}>
              <strong>{a.action}</strong>
              <p>
                {date(a.created_at)} · {a.actor}
              </p>
            </div>
          </div>
        ))}
      </Block>
      {selected && (
        <Drawer
          title={"Release " + selected.number}
          onClose={() => setSelected(null)}
        >
          <Status value="published" />
          <dl className="detail-list">
            <dt>Published</dt>
            <dd>{date(selected.created_at)}</dd>
            <dt>Documents</dt>
            <dd>
              {Array.isArray(selected.manifest.document_ids)
                ? selected.manifest.document_ids.length
                : 0}
            </dd>
            <dt>Evidence excerpts</dt>
            <dd>
              {Array.isArray(selected.manifest.chunk_ids)
                ? selected.manifest.chunk_ids.length
                : 0}
            </dd>
          </dl>
          <details className="advanced">
            <summary>Advanced release manifest</summary>
            <div>
              <pre
                style={{
                  fontSize: 10,
                  whiteSpace: "pre-wrap",
                  overflowWrap: "anywhere",
                }}
              >
                {JSON.stringify(selected.manifest, null, 2)}
              </pre>
            </div>
          </details>
        </Drawer>
      )}
    </div>
  );
}
