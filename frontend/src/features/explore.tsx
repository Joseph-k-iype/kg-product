import { useState } from "react";
import { Network, ArrowRight, Flag } from "lucide-react";
import { api, useData } from "../api/client";
import type { Entity, Neighborhood, Lineage, LineageNode } from "../api/types";
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
} from "../components/shared";
import { scoped, useProduct } from "./product";
export function ExplorerPage() {
  const { product } = useProduct();
  const [query, setQuery] = useState(""),
    [type, setType] = useState(""),
    [selected, setSelected] = useState<Entity | null>(null),
    [reason, setReason] = useState(""),
    [mode, setMode] = useState("list");
  const path = scoped(
    "entities?q=" +
      encodeURIComponent(query) +
      "&entity_type=" +
      encodeURIComponent(type),
  );
  const { data, error, loading } = useData<{
    items: Entity[];
    build: { instance_count: number; relationship_count: number };
  }>(path);
  const neighborPath = scoped(
    "entities/" + encodeURIComponent(selected?.id || "") + "/neighbors",
  );
  const { data: neighbors } = useData<Neighborhood>(
    selected ? neighborPath : null,
  );
  const { busy, run } = useNotice();
  const flagPath = scoped(
    "entities/" + encodeURIComponent(selected?.id || "") + "/flags",
  );
  return (
    <>
      <div className="guidance">
        <h3>Explore facts, with the evidence behind them.</h3>
        <p>
          Explore imported records and facts supported by documents. Open a
          record to see its attributes, relationships, and original evidence.
          Document fact extraction remains fixture-backed in this local demo.
        </p>
      </div>
      <div className="filters">
        <Field label="Search facts">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="A customer, complaint, or useful fact…"
          />
        </Field>
        <Field label="Fact type">
          <input
            value={type}
            onChange={(e) => setType(e.target.value)}
            placeholder="All types"
          />
        </Field>
        <button
          onClick={() => setMode(mode === "list" ? "connections" : "list")}
        >
          {mode === "list" ? "Show connections" : "Show list"}
        </button>
      </div>
      <Block
        title="Knowledge facts"
        subtitle={
          data
            ? `${data.build.instance_count} facts · ${data.build.relationship_count} relationships in this version`
            : "Prepare knowledge before exploring facts."
        }
      >
        {error ? (
          <Empty
            title="Facts are not ready yet"
            description={error}
            action={
              <a
                className="button"
                href={"/products/" + product.id + "/processing"}
              >
                Prepare knowledge
              </a>
            }
          />
        ) : loading ? (
          <Loading />
        ) : data?.items.length ? (
          mode === "list" ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Fact</th>
                    <th>Type</th>
                    <th>Supporting evidence</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((entity) => (
                    <tr key={entity.id}>
                      <td className="text-wrap">
                        <strong>{entity.label}</strong>
                        <div className="subtext">{entity.id}</div>
                      </td>
                      <td>
                        {entity.type_label ||
                          entity.type.replace(/([a-z])([A-Z])/g, "$1 $2")}
                      </td>
                      <td>
                        {entity.evidence.length} source excerpt
                        {entity.evidence.length === 1 ? "" : "s"}
                        <div className="subtext">{entity.provenance_label}</div>
                      </td>
                      <td>
                        <button onClick={() => setSelected(entity)}>
                          Inspect evidence <ArrowRight size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="fact-canvas">
              {data.items.slice(0, 8).map((e) => (
                <button
                  className="fact-node"
                  key={e.id}
                  onClick={() => setSelected(e)}
                >
                  <Network size={20} />
                  {e.label}
                  <small>
                    {e.type} · {e.evidence.length} evidence excerpts
                  </small>
                </button>
              ))}
              <p>Open a fact to expand its bounded neighborhood.</p>
            </div>
          )
        ) : (
          <Empty
            title="No matching facts"
            description="Try another name or fact type."
          />
        )}
      </Block>
      {selected && (
        <Drawer title={selected.label} onClose={() => setSelected(null)}>
          <Status value="ready" label={selected.provenance_label} />
          <dl className="detail-list">
            {Object.entries(selected.attributes).map(([key, value]) => (
              <div key={key} style={{ display: "contents" }}>
                <dt>
                  {selected.attribute_labels?.[key] || key.replaceAll("_", " ")}
                </dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
          <h3>Supporting evidence</h3>
          {selected.evidence.map((e, i) => (
            <div className="evidence" key={i}>
              <blockquote>{e.text}</blockquote>
              <small>
                {e.source_row
                  ? `Record ${e.source_row} · `
                  : e.source_subject
                    ? `Subject ${e.source_subject} · `
                    : ""}
                Characters {e.start}–{e.end} in prepared evidence
              </small>
              <EvidenceLink id={e.document_id} />
            </div>
          ))}
          <h3 style={{ marginTop: 25 }}>Related facts</h3>
          {neighbors && (
            <>
              <div className="fact-canvas">
                {neighbors.nodes.map((n) => (
                  <button
                    key={n.id}
                    className="fact-node"
                    onClick={() => setSelected(n)}
                  >
                    {n.label}
                    <small>{n.type}</small>
                  </button>
                ))}
              </div>
              {neighbors.relationships.map((r, i) => (
                <p key={i} className="content-note">
                  {r.source} → {r.type.replaceAll("_", " ").toLowerCase()} →{" "}
                  {r.target}
                </p>
              ))}
            </>
          )}
          <div style={{ marginTop: 25 }}>
            <Field
              label="Flag a correction"
              hint="Explain which fact or relationship needs review."
            >
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </Field>
            <button
              disabled={busy || !reason.trim()}
              style={{ marginTop: 12 }}
              onClick={() =>
                run("Correction flagged for review", async () => {
                  await api(flagPath, "POST", { reason });
                  setReason("");
                })
              }
            >
              <Flag size={14} />
              Flag for review
            </button>
          </div>
          <details className="advanced" style={{ marginTop: 25 }}>
            <summary>Advanced provenance</summary>
            <div>
              <p>Definition: {selected.iri}</p>
              <p>Build: {selected.build_id}</p>
              <p>Extraction version: {selected.extraction_version}</p>
            </div>
          </details>
        </Drawer>
      )}
    </>
  );
}
export function LineagePage() {
  const { product, revision } = useProduct();
  const path = scoped("lineage");
  const { data, error, loading } = useData<Lineage>(path);
  const [view, setView] = useState("trail"),
    [selected, setSelected] = useState<LineageNode | null>(null);
  const businessTypes: Record<string, string> = {
    source: "Sources",
    document: "Original documents",
    extracted: "Readable documents",
    chunk: "Evidence excerpts",
    embedding: "Searchable evidence",
    ontology: "Business concepts",
    mapping: "Representation settings",
    graph: "Supported facts",
    release: "Published release",
    consumer: "Connected apps",
  };
  return (
    <>
      <div className="guidance">
        <h3>Follow your knowledge back to its source.</h3>
        <p>
          Every excerpt, fact, and release keeps its supporting evidence. This
          trail describes revision {revision.number}; connected apps appear when
          viewing the release they use.
        </p>
      </div>
      <Block
        title={data?.label || "Evidence trail"}
        action={
          <button onClick={() => setView(view === "trail" ? "table" : "trail")}>
            {view === "trail" ? "Show table" : "Show visual trail"}
          </button>
        }
      >
        {error ? (
          <ErrorState message={error} />
        ) : loading ? (
          <Loading />
        ) : data && data.nodes.length ? (
          view === "trail" ? (
            <div className="trail-grid">
              {Object.entries(businessTypes).map(([type, label]) => {
                const nodes = data.nodes.filter((n) => n.type === type);
                return nodes.length ? (
                  <div key={type}>
                    <h3 style={{ fontSize: 11, marginBottom: 15 }}>{label}</h3>
                    {nodes.map((n) => (
                      <button
                        className="trail-node"
                        style={{ width: "100%", marginBottom: 12 }}
                        key={n.id}
                        onClick={() => setSelected(n)}
                      >
                        <span>
                          {n.type === "source" ? "Document origin" : n.label}
                        </span>
                        <small>
                          {data.edges.filter((e) => e.target === n.id).length}{" "}
                          inputs ·{" "}
                          {data.edges.filter((e) => e.source === n.id).length}{" "}
                          dependencies
                        </small>
                        <ArrowRight size={13} />
                      </button>
                    ))}
                  </div>
                ) : null;
              })}
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Record</th>
                    <th>Representation</th>
                    <th>Depends on</th>
                    <th>Inspect</th>
                  </tr>
                </thead>
                <tbody>
                  {data.nodes.map((n) => (
                    <tr key={n.id}>
                      <td>{n.label}</td>
                      <td>{businessTypes[n.type]}</td>
                      <td>
                        {data.edges
                          .filter((e) => e.target === n.id)
                          .map(
                            (e) =>
                              data.nodes.find((x) => x.id === e.source)?.label,
                          )
                          .join(", ") || "Original input"}
                      </td>
                      <td>
                        <button onClick={() => setSelected(n)}>Details</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : (
          <Empty
            title="Your evidence trail starts with documents"
            description="Add and prepare documents to see how they support your knowledge."
          />
        )}
      </Block>
      {selected && (
        <Drawer title={selected.label} onClose={() => setSelected(null)}>
          <dl className="detail-list">
            {Object.entries(selected)
              .filter(
                ([k]) =>
                  ![
                    "id",
                    "record_id",
                    "object_key",
                    "sha256",
                    "model",
                    "model_revision",
                  ].includes(k),
              )
              .map(([key, value]) => (
                <div key={key} style={{ display: "contents" }}>
                  <dt>{key.replaceAll("_", " ")}</dt>
                  <dd>{String(value)}</dd>
                </div>
              ))}
          </dl>
          {selected.type === "document" && (
            <EvidenceLink id={selected.record_id} />
          )}
          <h3>Dependencies</h3>
          {data?.edges
            .filter((e) => e.target === selected.id || e.source === selected.id)
            .map((e, i) => (
              <p style={{ marginTop: 12, fontSize: 11 }} key={i}>
                {data.nodes.find((n) => n.id === e.source)?.label} → {e.label} →{" "}
                {data.nodes.find((n) => n.id === e.target)?.label}
              </p>
            ))}
          <details className="advanced" style={{ marginTop: 20 }}>
            <summary>Advanced version metadata</summary>
            <div>
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  overflowWrap: "anywhere",
                  fontSize: 10,
                }}
              >
                {JSON.stringify(selected, null, 2)}
              </pre>
            </div>
          </details>
        </Drawer>
      )}
    </>
  );
}
