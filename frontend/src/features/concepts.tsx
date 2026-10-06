import { useEffect, useState } from "react";
import { Plus, Boxes, ShieldCheck, FileCode } from "lucide-react";
import { api, ApiError, useData } from "../api/client";
import type { Ontology, Concept, PropertyDefinition, Rule } from "../api/types";
import {
  Block,
  Field,
  Status,
  Empty,
  ErrorState,
  Loading,
  useNotice,
  NextLink,
} from "../components/shared";
import { scoped, useProduct } from "./product";
function key(iri: string) {
  return (
    iri
      .split(/[/#]/)
      .pop()
      ?.replace(/[^A-Za-z0-9_]/g, "") || "Concept"
  );
}
function defaultMapping(d: Ontology) {
  return {
    classes: d.classes.map((c) => ({
      iri: c.iri,
      label:
        d.mapping?.classes.find((m) => m.iri === c.iri)?.label || key(c.iri),
    })),
    properties: d.properties.map((p) => ({
      iri: p.iri,
      key:
        d.mapping?.properties.find((m) => m.iri === p.iri)?.key ||
        (p.kind === "object" ? key(p.iri).toUpperCase() : key(p.iri)),
      kind: p.kind,
    })),
    expected_generation: d.generation,
  };
}
export function ConceptsPage() {
  const { product, readonly } = useProduct();
  const path = scoped("ontology");
  const { data, error, loading } = useData<Ontology>(path);
  const { busy, run } = useNotice();
  const [view, setView] = useState("classes"),
    [search, setSearch] = useState(""),
    [selected, setSelected] = useState(""),
    [label, setLabel] = useState(""),
    [description, setDescription] = useState(""),
    [parent, setParent] = useState(""),
    [domain, setDomain] = useState(""),
    [range, setRange] = useState("http://www.w3.org/2001/XMLSchema#string"),
    [target, setTarget] = useState(""),
    [property, setProperty] = useState(""),
    [originalProperty, setOriginalProperty] = useState(""),
    [min, setMin] = useState(1),
    [max, setMax] = useState<number | null>(1),
    [rdf, setRdf] = useState(""),
    [mapText, setMapText] = useState(""),
    [mode, setMode] = useState("merge"),
    [preview, setPreview] = useState<{
      impact_token: string;
      removed_concepts: string[];
      rebuild_steps: string[];
      affected_instance_count?: number;
    } | null>(null),
    [pendingEdit, setPendingEdit] = useState<Record<string, unknown> | null>(
      null,
    ),
    [namespace, setNamespace] = useState(""),
    [prefix, setPrefix] = useState(""),
    [sample, setSample] = useState(""),
    [findings, setFindings] = useState<
      { message: string; entity_id: string }[]
    >([]);
  const sub = (suffix: string) =>
    path.replace("/ontology?", "/ontology/" + suffix + "?");
  useEffect(() => {
    if (data) {
      setRdf(data.turtle);
      setMapText(JSON.stringify(defaultMapping(data), null, 2));
    }
  }, [data]);
  const clear = () => {
    setSelected("");
    setLabel("");
    setDescription("");
    setParent("");
    setDomain("");
    setTarget("");
    setProperty("");
    setOriginalProperty("");
    setMin(1);
    setMax(1);
  };
  const pick = (item: Concept | PropertyDefinition | Rule) => {
    setSelected(item.iri);
    if ("label" in item) {
      setLabel(item.label);
      setDescription(item.description);
      if ("parent" in item) setParent(item.parent);
      if ("domain" in item) {
        setDomain(item.domain);
        setRange(item.range);
      }
    } else {
      setTarget(item.target);
      setProperty(item.path);
      setOriginalProperty(item.path);
      setMin(item.min_count);
      setMax(item.max_count);
      setRange(item.datatype);
    }
  };
  const save = () =>
    run("Concepts and rules saved", async () => {
      const iri =
        selected ||
        "https://knowledge.example/" +
          (label.trim().replace(/[^A-Za-z0-9]/g, "") || "Rule") +
          "_" +
          crypto.randomUUID().slice(0, 8);
      const payload =
        view === "classes"
          ? { kind: "class", iri, label, description, parent }
          : view === "rules"
            ? {
                kind: "shape",
                iri,
                target,
                path: property,
                original_path: selected ? originalProperty : undefined,
                min_count: min,
                max_count: max,
                datatype: range,
              }
            : {
                kind: view === "relationships" ? "object" : "datatype",
                iri,
                label,
                description,
                domain,
                range,
              };
      const edit = { ...payload, expected_generation: data?.generation };
      try {
        const next = await api<Ontology>(path, "PATCH", edit);
        if (view !== "rules")
          await api(sub("mapping"), "PUT", defaultMapping(next));
        clear();
      } catch (e) {
        if (
          e instanceof ApiError &&
          e.status === 409 &&
          (e.detail as { code: string }).code === "impact_required"
        ) {
          setPendingEdit(edit);
          setPreview(await api(sub("preview-edit"), "POST", edit));
          return;
        }
        throw e;
      }
    });
  const replace = () =>
    run("Definition changes saved", async () => {
      if (pendingEdit) {
        const next = await api<Ontology>(path, "PATCH", {
          ...pendingEdit,
          impact_token: preview?.impact_token,
        });
        if (pendingEdit.kind !== "shape")
          await api(sub("mapping"), "PUT", defaultMapping(next));
        setPendingEdit(null);
        clear();
      } else
        await api(sub("import"), "POST", {
          turtle: rdf,
          mode,
          impact_token: preview?.impact_token,
          expected_generation: data?.generation,
        });
      setPreview(null);
    });
  const remove = () =>
    run("Definition removed after impact review", async () => {
      try {
        await api(path, "PATCH", {
          kind: "delete",
          iri: selected,
          expected_generation: data?.generation,
        });
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          const detail = e.detail as { proposed_turtle: string };
          setRdf(detail.proposed_turtle);
          setMode("replace");
          setPreview(
            await api(sub("impact"), "POST", {
              turtle: detail.proposed_turtle,
              mode: "replace",
            }),
          );
          return;
        }
        throw e;
      }
    });
  if (loading) return <Loading />;
  if (error || !data)
    return <ErrorState message={error || "Concept definitions unavailable"} />;
  const items =
    view === "classes"
      ? data.classes
      : view === "rules"
        ? data.shapes
        : data.properties.filter(
            (p) =>
              p.kind === (view === "relationships" ? "object" : "datatype"),
          );
  return (
    <>
      <div className="guidance">
        <h2>Define what your knowledge means.</h2>
        <p>
          Concepts are the things your team talks about. Attributes describe
          them. Rules say what a complete, reliable fact must contain. Technical
          representation settings are prepared automatically for guided edits.
        </p>
      </div>
      {!data.classes.length && !readonly && (
        <Block title="Start with a business template">
          <div className="block-body">
            <p style={{ marginBottom: 15 }}>
              Choose a simple starting point. You can change the labels and
              rules later.
            </p>
            <button
              className="primary"
              disabled={busy}
              onClick={() =>
                run("Starter concepts added", () =>
                  api(sub("starter"), "POST", { template: "general" }),
                )
              }
            >
              Use general knowledge starter
            </button>
            <button
              style={{ marginLeft: 10 }}
              disabled={busy}
              onClick={() =>
                run("Customer support concepts added", () =>
                  api(sub("starter"), "POST", { template: "customer-support" }),
                )
              }
            >
              Use customer support starter
            </button>
          </div>
        </Block>
      )}
      <nav className="tabs" aria-label="Concept views">
        {[
          ["classes", "Concepts"],
          ["attributes", "Attributes"],
          ["relationships", "Relationships"],
          ["rules", "Business Rules"],
        ].map(([id, title]) => (
          <button
            key={id}
            className={view === id ? "active" : ""}
            onClick={() => {
              setView(id);
              clear();
            }}
          >
            {title}
          </button>
        ))}
      </nav>
      <div className="concept-grid">
        <Block
          title={view === "rules" ? "Rules" : "Business definitions"}
          action={
            !readonly && (
              <button
                className="icon-button"
                aria-label="Add definition"
                onClick={clear}
              >
                <Plus size={17} />
              </button>
            )
          }
        >
          <div className="block-body">
            <Field label="Find a definition">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search names…"
              />
            </Field>
          </div>
          {items
            .filter((i) =>
              ("label" in i ? i.label : i.iri)
                .toLowerCase()
                .includes(search.toLowerCase()),
            )
            .map((item) => (
              <div
                key={item.iri + ("path" in item ? ":" + item.path : "")}
                className={
                  "concept-item " +
                  (selected === item.iri &&
                  (!("path" in item) || originalProperty === item.path)
                    ? "selected"
                    : "")
                }
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter") pick(item);
                }}
                onClick={() => pick(item)}
              >
                <span className="round-icon">
                  {view === "rules" ? <ShieldCheck /> : <Boxes />}
                </span>
                <div>
                  <h3>
                    {"label" in item
                      ? item.label
                      : "Rule for " +
                        (data.classes.find((c) => c.iri === item.target)
                          ?.label || key(item.target))}
                  </h3>
                  <p>
                    {"description" in item
                      ? item.description
                      : "Required values and supported constraints"}
                  </p>
                </div>
              </div>
            ))}
          {!items.length && (
            <Empty
              title="No definitions yet"
              description="Add a concept or choose a starter."
            />
          )}
        </Block>
        <Block
          title={
            selected
              ? "Edit definition"
              : view === "rules"
                ? "Add a business rule"
                : view === "classes"
                  ? "Add a concept"
                  : "Add an attribute or relationship"
          }
          subtitle="Simple forms. Stable meaning across every release."
        >
          <form
            className="definition-form"
            onSubmit={(e) => {
              e.preventDefault();
              save();
            }}
          >
            {view === "rules" ? (
              <>
                <Field label="Applies to concept">
                  <select
                    required
                    value={target}
                    disabled={readonly}
                    onChange={(e) => setTarget(e.target.value)}
                  >
                    <option value="">Choose concept</option>
                    {data.classes.map((c) => (
                      <option key={c.iri} value={c.iri}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Required attribute">
                  <select
                    required
                    value={property}
                    disabled={readonly}
                    onChange={(e) => setProperty(e.target.value)}
                  >
                    <option value="">Choose attribute</option>
                    {data.properties
                      .filter((p) => p.kind === "datatype")
                      .map((p) => (
                        <option key={p.iri} value={p.iri}>
                          {p.label}
                        </option>
                      ))}
                  </select>
                </Field>
                <div className="form-grid">
                  <Field label="Minimum values">
                    <input
                      type="number"
                      min={0}
                      value={min}
                      disabled={readonly}
                      onChange={(e) => setMin(Number(e.target.value))}
                    />
                  </Field>
                  <Field
                    label="Maximum values"
                    hint="Leave empty for no maximum."
                  >
                    <input
                      type="number"
                      min={min}
                      value={max ?? ""}
                      placeholder="No maximum"
                      disabled={readonly}
                      onChange={(e) =>
                        setMax(
                          e.target.value === "" ? null : Number(e.target.value),
                        )
                      }
                    />
                  </Field>
                </div>
                <Field label="Value type">
                  <select
                    value={range}
                    disabled={readonly}
                    onChange={(e) => setRange(e.target.value)}
                  >
                    <option value="http://www.w3.org/2001/XMLSchema#string">
                      Text
                    </option>
                    <option value="http://www.w3.org/2001/XMLSchema#integer">
                      Whole number
                    </option>
                    <option value="http://www.w3.org/2001/XMLSchema#date">
                      Date
                    </option>
                  </select>
                </Field>
                <div className="guidance">
                  Every{" "}
                  {data.classes.find((c) => c.iri === target)?.label ||
                    "selected concept"}{" "}
                  must have{" "}
                  {max === null
                    ? `at least ${min}`
                    : min === max
                      ? `exactly ${min}`
                      : `between ${min} and ${max}`}{" "}
                  {data.properties.find((p) => p.iri === property)?.label ||
                    "selected attribute"}{" "}
                  value{max === 1 ? "" : "s"}.
                </div>
              </>
            ) : (
              <>
                <Field
                  label={
                    view === "classes" ? "Concept name" : "Definition name"
                  }
                >
                  <input
                    required
                    disabled={readonly}
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                    placeholder={
                      view === "classes"
                        ? "e.g. Complaint"
                        : "e.g. Complaint identifier"
                    }
                  />
                </Field>
                <Field label="Meaning in business language">
                  <textarea
                    value={description}
                    disabled={readonly}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="What does this mean to your team?"
                  />
                </Field>
                {view === "classes" ? (
                  <Field label="Part of a broader concept">
                    <select
                      value={parent}
                      disabled={readonly}
                      onChange={(e) => setParent(e.target.value)}
                    >
                      <option value="">No broader concept</option>
                      {data.classes
                        .filter((c) => c.iri !== selected)
                        .map((c) => (
                          <option key={c.iri} value={c.iri}>
                            {c.label}
                          </option>
                        ))}
                    </select>
                  </Field>
                ) : (
                  <>
                    <Field label="Describes concept">
                      <select
                        required
                        value={domain}
                        disabled={readonly}
                        onChange={(e) => setDomain(e.target.value)}
                      >
                        <option value="">Choose concept</option>
                        {data.classes.map((c) => (
                          <option key={c.iri} value={c.iri}>
                            {c.label}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field
                      label={
                        view === "relationships"
                          ? "Related concept"
                          : "Value type"
                      }
                    >
                      <select
                        value={range}
                        disabled={readonly}
                        onChange={(e) => setRange(e.target.value)}
                      >
                        {view === "relationships" ? (
                          <>
                            <option value="">Choose related concept</option>
                            {data.classes.map((c) => (
                              <option key={c.iri} value={c.iri}>
                                {c.label}
                              </option>
                            ))}
                          </>
                        ) : (
                          <>
                            <option value="http://www.w3.org/2001/XMLSchema#string">
                              Text
                            </option>
                            <option value="http://www.w3.org/2001/XMLSchema#integer">
                              Whole number
                            </option>
                            <option value="http://www.w3.org/2001/XMLSchema#date">
                              Date
                            </option>
                          </>
                        )}
                      </select>
                    </Field>
                  </>
                )}
              </>
            )}
            {!readonly && (
              <div className="form-actions">
                {selected && (
                  <button
                    type="button"
                    className="danger"
                    disabled={busy}
                    onClick={remove}
                  >
                    Preview removal
                  </button>
                )}
                <button className="primary" disabled={busy}>
                  {view === "rules" ? "Save business rule" : "Save definition"}
                </button>
              </div>
            )}
          </form>
        </Block>
        <div className="context-column">
          <Block title="Definition details">
            <div className="block-body">
              <Status
                value={data.id ? "ready" : "draft"}
                label={"Definition version " + data.version}
              />
              <p style={{ fontSize: 11, marginTop: 15 }}>
                Saving changes creates a new definition version. Prepare
                knowledge and run fresh checks before publication.
              </p>
              {selected && (
                <p style={{ fontSize: 11, marginTop: 15 }}>
                  This identifier stays stable when you rename the definition.
                </p>
              )}
            </div>
          </Block>
          <Block title="Next steps">
            <div className="block-body">
              <NextLink to={"/products/" + product.id + "/processing"}>
                Prepare knowledge
              </NextLink>
              <p style={{ fontSize: 10, marginTop: 12 }}>
                Then check your business rules against the prepared facts.
              </p>
            </div>
          </Block>
        </div>
      </div>
      {preview && (
        <Block title="Review the change impact">
          <div className="block-body">
            <p>
              Removed concepts:{" "}
              {preview.removed_concepts.map(key).join(", ") || "None"}
            </p>
            <p>
              {preview.affected_instance_count ?? 0} existing facts affected.
            </p>
            <p>
              Existing published facts are preserved. Required next steps:{" "}
              {preview.rebuild_steps.join(" → ")}.
            </p>
            <div className="form-actions">
              <button
                onClick={() => {
                  setPreview(null);
                  setPendingEdit(null);
                }}
              >
                Cancel change
              </button>
              <button
                className="primary"
                disabled={busy || readonly}
                onClick={replace}
              >
                Apply reviewed change
              </button>
            </div>
          </div>
        </Block>
      )}
      <details className="advanced">
        <summary>
          Advanced — technical definitions, import, and representation settings
        </summary>
        <div>
          <p style={{ marginBottom: 15 }}>
            RDF/Turtle source and FalkorDB mappings are intended for technical
            administrators. The business forms above handle the usual tasks.
          </p>
          {data.unsupported_constructs.length > 0 && (
            <ErrorState
              message={
                "Unsupported constructs: " +
                data.unsupported_constructs.join(", ")
              }
            />
          )}
          <Field label="Import a Turtle definition file">
            <input
              type="file"
              accept=".ttl"
              disabled={readonly}
              onChange={async (e) => {
                if (e.target.files?.[0]) setRdf(await e.target.files[0].text());
              }}
            />
          </Field>
          <Field label="RDF source">
            <textarea
              className="source-editor"
              value={rdf}
              disabled={readonly}
              onChange={(e) => {
                setRdf(e.target.value);
                setPreview(null);
              }}
            />
          </Field>
          <div className="filters">
            <Field label="Import behavior">
              <select
                value={mode}
                disabled={readonly}
                onChange={(e) => {
                  setMode(e.target.value);
                  setPreview(null);
                }}
              >
                <option value="merge">Merge with current definitions</option>
                <option value="replace">Replace after impact review</option>
              </select>
            </Field>
            <button
              disabled={busy || readonly}
              onClick={() =>
                mode === "replace"
                  ? run("Impact preview ready", async () =>
                      setPreview(
                        await api(sub("impact"), "POST", { turtle: rdf, mode }),
                      ),
                    )
                  : replace()
              }
            >
              {mode === "replace"
                ? "Preview replacement impact"
                : "Save merged definitions"}
            </button>
            <a
              className="button"
              href={"/api" + sub("export")}
              download="ontology.ttl"
            >
              <FileCode size={14} />
              Export definitions
            </a>
          </div>
          <Field label="Representation mapping JSON">
            <textarea
              className="source-editor"
              value={mapText}
              disabled={readonly}
              onChange={(e) => setMapText(e.target.value)}
            />
          </Field>
          <button
            disabled={busy || readonly}
            onClick={() =>
              run("Representation settings saved", () =>
                api(sub("mapping"), "PUT", {
                  ...JSON.parse(mapText),
                  expected_generation: data.generation,
                }),
              )
            }
          >
            Validate and save mappings
          </button>
          <h3 style={{ margin: "25px 0 10px" }}>Namespaces</h3>
          <div className="filters">
            {data.namespaces.map((n) => (
              <span className="tag" key={n.prefix}>
                {n.prefix}: {n.iri}
              </span>
            ))}
          </div>
          <div className="form-grid">
            <Field label="Namespace prefix">
              <input
                value={prefix}
                disabled={readonly}
                onChange={(e) => setPrefix(e.target.value)}
              />
            </Field>
            <Field label="Namespace IRI">
              <input
                value={namespace}
                disabled={readonly}
                onChange={(e) => setNamespace(e.target.value)}
              />
            </Field>
          </div>
          <button
            disabled={busy || readonly || !prefix || !namespace}
            style={{ marginTop: 12 }}
            onClick={() =>
              run("Namespace saved", () =>
                api(path, "PATCH", {
                  kind: "namespace",
                  iri: namespace,
                  prefix,
                  expected_generation: data.generation,
                }),
              )
            }
          >
            Add namespace
          </button>
          <h3 style={{ margin: "25px 0 10px" }}>Validate sample facts</h3>
          <Field label="Sample Turtle facts">
            <textarea
              className="source-editor"
              value={sample}
              onChange={(e) => setSample(e.target.value)}
            />
          </Field>
          <button
            disabled={busy || !sample}
            onClick={() =>
              run("Sample validation complete", async () => {
                const result = await api<{
                  findings: { message: string; entity_id: string }[];
                }>(sub("validate-sample"), "POST", { turtle: sample });
                setFindings(result.findings);
              })
            }
          >
            Validate sample
          </button>
          {findings.map((f, i) => (
            <div className="error" key={i}>
              {f.entity_id}: {f.message}
            </div>
          ))}
        </div>
      </details>
    </>
  );
}
