import { useState, useEffect } from "react";
import { Search, Plus, Link2, ArrowRight } from "lucide-react";
import { api, useData } from "@/api/client";
import type { Retrieval, Release, Consumer } from "@/api/types";
import {
  Block,
  Field,
  Status,
  Empty,
  EvidenceLink,
  useNotice,
  ErrorState,
  Loading,
  Drawer,
} from "@/components/shared";
import { useProduct } from "@/features/product/context";
export function RetrievalPage() {
  const { product, revision, readonly } = useProduct();
  const { data: releases } = useData<Release[]>(
    "/products/" + product.id + "/releases",
  );
  const [query, setQuery] = useState(""),
    [mode, setMode] = useState("vector"),
    [version, setVersion] = useState(readonly ? "" : "draft"),
    [limit, setLimit] = useState(Number(revision.config.limit) || 5),
    [result, setResult] = useState<Retrieval | null>(null),
    [selected, setSelected] = useState(0);
  const { busy, run } = useNotice();
  const search = () =>
    run("Search complete", async () => {
      const value = await api<Retrieval>(
        "/products/" + product.id + "/retrieval",
        "POST",
        {
          query,
          mode,
          limit,
          preview: version === "draft",
          revision_id: revision.id,
          release_id: version === "draft" ? undefined : version,
        },
      );
      setResult(value);
      setSelected(0);
    });
  useEffect(() => {
    if (readonly && !version && releases) {
      setVersion(releases.find((r) => r.revision_id === revision.id)?.id || "");
    }
  }, [readonly, version, releases, revision.id]);
  const hit = result?.results[selected];
  return (
    <>
      <div className="guidance">
        <h2>Find answers. See the evidence.</h2>
        <p>
          Search ranks passages from your selected version. Read the evidence
          and open the original document to verify it. This MVP returns evidence
          rather than generated answers.
        </p>
      </div>
      <form
        className="search-bar"
        onSubmit={(e) => {
          e.preventDefault();
          search();
        }}
      >
        <Field label="Your question">
          <input
            required
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. How long do customers have to request a refund?"
          />
        </Field>
        <Field label="Search version">
          <select
            value={version}
            onChange={(e) => {
              setVersion(e.target.value);
              setResult(null);
            }}
          >
            {!readonly && (
              <option value="draft">Draft preview — unpublished</option>
            )}
            {releases?.map((r) => (
              <option key={r.id} value={r.id}>
                Published release {r.number}
                {r.id === product.active_release_id ? " · Active" : ""}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Search method">
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="vector">Meaning-based search</option>
            <option value="graph" disabled={!revision.graph_build_id}>
              Fact lookup
            </option>
            <option value="hybrid" disabled={!revision.graph_build_id}>
              Meaning + related facts
            </option>
          </select>
        </Field>
        <button className="primary" disabled={busy || !query.trim()}>
          <Search size={15} />
          {busy ? "Searching…" : "Search"}
        </button>
      </form>
      <div className="grid-equal">
        <Block
          title={
            result
              ? `${result.results.length} evidence results`
              : "Search your knowledge"
          }
          subtitle={result?.label || "Select a version and ask a question."}
        >
          {result?.results.length ? (
            result.results.map((r, i) => (
              <div
                key={r.evidence?.chunk_id || i}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter") setSelected(i);
                }}
                onClick={() => setSelected(i)}
                className={"result-row " + (selected === i ? "selected" : "")}
              >
                <span className="rank">{i + 1}</span>
                <div>
                  <h3>
                    {r.entity?.label ||
                      r.evidence.document_name ||
                      "Source passage"}
                  </h3>
                  <p>{r.evidence?.text}</p>
                  {r.evidence && <EvidenceLink id={r.evidence.document_id} />}
                  <div>
                    <Status
                      value="ready"
                      label={
                        r.score === null
                          ? "Supported fact"
                          : Math.round(Math.max(0, r.score) * 100) +
                            "% similarity"
                      }
                    />
                  </div>
                </div>
                <ArrowRight size={13} />
              </div>
            ))
          ) : (
            <Empty
              title={
                result ? "No matching evidence" : "Ask a business question"
              }
              description={
                result
                  ? "Try another wording or fact identifier."
                  : "Your results will include the exact passages and source documents."
              }
            />
          )}
        </Block>
        <Block
          title="Supporting evidence"
          subtitle="Open a result to inspect its original source."
        >
          {hit ? (
            <div className="block-body">
              <h3>
                {hit.entity?.label ||
                  hit.evidence.document_name ||
                  "Evidence passage"}
              </h3>
              <div className="evidence">
                <blockquote>{hit.evidence?.text}</blockquote>
                {hit.evidence && (
                  <>
                    <p className="content-note">
                      Source characters {hit.evidence.start}–{hit.evidence.end}
                    </p>
                    <EvidenceLink id={hit.evidence.document_id}>
                      Open source
                    </EvidenceLink>
                  </>
                )}
              </div>
              {hit.related_facts?.map((context, i) => (
                <div key={i}>
                  <h3 style={{ marginTop: 20 }}>Related facts</h3>
                  {context.nodes.map((n) => (
                    <p key={n.id} style={{ fontSize: 11, marginTop: 8 }}>
                      {n.label} · {n.type}
                    </p>
                  ))}
                  {context.relationships.map((e, j) => (
                    <p className="content-note" key={j}>
                      {e.source} → {e.type.replaceAll("_", " ")} → {e.target}
                    </p>
                  ))}
                </div>
              ))}
              <button
                style={{ marginTop: 20 }}
                disabled={busy}
                onClick={() =>
                  run("Question saved as an evaluation case", () =>
                    api(
                      "/products/" + product.id + "/evaluation-cases",
                      "POST",
                      {
                        query,
                        expected_document_ids: [hit.evidence.document_id],
                      },
                    ),
                  )
                }
              >
                Save as evaluation question
              </button>
            </div>
          ) : (
            <Empty
              title="Evidence you can check"
              description="Every result links to a source document. Draft results are clearly labeled and never replace published knowledge."
            />
          )}
        </Block>
      </div>
      <details className="advanced">
        <summary>Advanced search settings & diagnostics</summary>
        <div>
          <Field label="Result limit">
            <input
              type="number"
              min={1}
              max={50}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
            />
          </Field>
          <p className="content-note">
            Meaning-based search uses the same pinned local embedding model as
            document preparation. Missing models report an actionable error.
          </p>
          {result && (
            <pre style={{ fontSize: 10, whiteSpace: "pre-wrap" }}>
              {JSON.stringify(result.diagnostics, null, 2)}
            </pre>
          )}
        </div>
      </details>
    </>
  );
}
export function ConsumersPage() {
  const { product } = useProduct();
  const { data, error, loading } = useData<Consumer[]>(
    "/consumers?product_id=" + product.id,
  );
  const { data: releases } = useData<Release[]>(
    "/products/" + product.id + "/releases",
  );
  const [adding, setAdding] = useState(false),
    [id, setId] = useState<string | null>(null),
    [name, setName] = useState(""),
    [type, setType] = useState("copilot"),
    [policy, setPolicy] = useState("active"),
    [release, setRelease] = useState("");
  const { busy, run } = useNotice();
  const edit = (c: Consumer) => {
    setId(c.id);
    setName(c.name);
    setType(c.type);
    setPolicy(c.release_policy);
    setRelease(c.release_id || "");
    setAdding(true);
  };
  return (
    <>
      <Block
        title="Connected apps"
        subtitle="Choose which apps use this product, and how they receive new releases."
        action={
          <button
            className="primary"
            onClick={() => {
              setId(null);
              setName("");
              setAdding(true);
            }}
          >
            <Plus size={15} />
            Register app
          </button>
        }
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
                  <th>Application</th>
                  <th>Type</th>
                  <th>Release policy</th>
                  <th>Resolved release</th>
                  <th>Usage</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {data.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <span className="product-cell">
                        <span className="round-icon">
                          <Link2 />
                        </span>
                        <strong>{c.name}</strong>
                      </span>
                    </td>
                    <td>{c.type === "api" ? "API application" : c.type}</td>
                    <td>
                      {c.release_policy === "active"
                        ? "Follow active release"
                        : "Pinned release"}
                    </td>
                    <td>
                      {c.resolved.release_id
                        ? "Release " + c.resolved.number
                        : "Awaiting publication"}
                    </td>
                    <td>
                      {c.usage.requests_last_7_days}
                      <div className="subtext">{c.usage.label}</div>
                    </td>
                    <td>
                      <button onClick={() => edit(c)}>Edit policy</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="Register an app that uses this knowledge"
            description="Agents, copilots, API applications, and dashboards can follow the active release or stay pinned to a version."
          />
        )}
      </Block>
      <div className="grid-equal">
        <Block title="Follow active releases">
          <div className="block-body">
            <p>
              Receive the latest approved knowledge whenever a new release is
              published. Your apps resolve a consistent set of documents,
              concepts, and facts.
            </p>
          </div>
        </Block>
        <Block title="Pin to a release">
          <div className="block-body">
            <p>
              Keep using a specific version until you choose to change it. New
              publications do not change the knowledge your pinned app uses.
            </p>
          </div>
        </Block>
      </div>
      {adding && (
        <Drawer
          title={id ? "Edit application policy" : "Register a connected app"}
          onClose={() => setAdding(false)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run("Application configuration saved", async () => {
                await api(
                  "/consumers" + (id ? "/" + id : ""),
                  id ? "PATCH" : "POST",
                  {
                    name,
                    type,
                    product_id: product.id,
                    release_policy: policy,
                    release_id: policy === "pinned" ? release : null,
                  },
                );
                setAdding(false);
              });
            }}
          >
            <Field label="Application name">
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Customer Support Copilot"
              />
            </Field>
            <Field label="Application type">
              <select value={type} onChange={(e) => setType(e.target.value)}>
                <option value="copilot">Copilot</option>
                <option value="agent">Agent</option>
                <option value="api">API application</option>
                <option value="dashboard">Dashboard</option>
              </select>
            </Field>
            <Field label="Release policy">
              <select
                value={policy}
                onChange={(e) => setPolicy(e.target.value)}
              >
                <option value="active">Follow the active release</option>
                <option value="pinned">Pin to a specific release</option>
              </select>
            </Field>
            {policy === "pinned" && (
              <Field label="Pinned release">
                <select
                  required
                  value={release}
                  onChange={(e) => setRelease(e.target.value)}
                >
                  <option value="">Choose a published release</option>
                  {releases?.map((r) => (
                    <option key={r.id} value={r.id}>
                      Release {r.number}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            <p className="content-note">
              Registration records this dependency. Demo usage is simulated and
              explicitly labeled.
            </p>
            <div className="form-actions">
              <button type="button" onClick={() => setAdding(false)}>
                Cancel
              </button>
              <button className="primary" disabled={busy}>
                Save application
              </button>
            </div>
          </form>
        </Drawer>
      )}
    </>
  );
}
