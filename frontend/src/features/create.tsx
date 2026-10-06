import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Check, Plug } from "lucide-react";
import { api } from "@/api/client";
import type { Product, Source } from "@/api/types";
import { useData } from "@/api/client";
import {
  PageTitle,
  Block,
  Field,
  useNotice,
  Status,
  ErrorState,
} from "@/components/shared";
import { DataFiles, SourceFields, initialSource } from "./data-intake";
import type { ImportFile } from "./data-intake";
const steps = [
  ["Purpose", "Define the goal and ownership"],
  ["Bring data", "Add files or choose a data source"],
  ["Concepts", "Choose a simple starting point"],
  ["Readiness", "Understand checks and search settings"],
  ["Summary", "Review and create a draft"],
] as const;
export function CreateProduct() {
  const [step, setStep] = useState(0),
    [name, setName] = useState(""),
    [purpose, setPurpose] = useState(""),
    [domain, setDomain] = useState("General"),
    [owner, setOwner] = useState("Maya Chen"),
    [files, setFiles] = useState<ImportFile[]>([]),
    [sourceId, setSource] = useState(""),
    [newSource, setNewSource] = useState(initialSource),
    [importSourceNow, setImportSourceNow] = useState(false),
    [connection, setConnection] = useState<{
      record_count: number;
      message: string;
      truncated?: boolean;
    } | null>(null),
    [connectionError, setConnectionError] = useState<string | null>(null),
    [testing, setTesting] = useState(false),
    [template, setTemplate] = useState("general"),
    [strict, setStrict] = useState(true),
    [limit, setLimit] = useState(5);
  const { data: sources } = useData<Source[]>("/sources");
  const { busy, run } = useNotice();
  const navigate = useNavigate();
  const chosenSource = sources?.find((s) => s.id === sourceId);
  const liveSource =
    sourceId === "new"
      ? ["postgres", "api"].includes(newSource.type)
      : !!chosenSource && ["postgres", "api"].includes(chosenSource.type);
  const fileErrors = files.some((f) => f.loading || f.error);
  const testSource = async () => {
    setTesting(true);
    setConnection(null);
    setConnectionError(null);
    try {
      setConnection(
        await api(
          sourceId === "new" ? "/sources/test" : `/sources/${sourceId}/test`,
          "POST",
          sourceId === "new" ? newSource : undefined,
        ),
      );
    } catch (error) {
      setConnectionError(
        error instanceof Error ? error.message : "Could not test this source.",
      );
    } finally {
      setTesting(false);
    }
  };
  const create = () =>
    run("Draft created", async () => {
      const form = new FormData();
      form.append(
        "metadata",
        JSON.stringify({
          name,
          purpose,
          domain,
          owner,
          config: { quality_gates: strict ? {} : { metadata: 0.75 }, limit },
          template,
          existing_source_id:
            sourceId && sourceId !== "new" ? sourceId : undefined,
          source: sourceId === "new" ? newSource : undefined,
          import_source_now: liveSource && importSourceNow,
        }),
      );
      files.forEach((item) => form.append("files", item.file));
      const p = await api<Product>("/onboarding", "POST", form);
      sessionStorage.setItem("currentProduct", p.id);
      navigate("/products/" + p.id);
      return p;
    });
  return (
    <>
      <PageTitle
        eyebrow="NEW KNOWLEDGE PRODUCT"
        title="Start with a purpose."
        description="Create a draft now. You can finish the setup at your own pace."
        action={
          <Link className="button" to="/products">
            <ArrowLeft size={14} />
            Back to products
          </Link>
        }
      />
      <div className="wizard">
        <div className="step-list">
          {steps.map(([title, desc], i) => (
            <button
              key={title}
              onClick={() => {
                if (i < step || name.trim()) setStep(i);
              }}
              className={step === i ? "active" : ""}
            >
              <span className="step-number">
                {i < step ? <Check size={13} /> : i + 1}
              </span>
              <span>
                {title}
                <small>{desc}</small>
              </span>
            </button>
          ))}
        </div>
        <Block>
          <form
            className="wizard-panel"
            onSubmit={(e) => {
              e.preventDefault();
              if (step < 4) setStep(step + 1);
              else create();
            }}
          >
            <div className="wizard-step-caption">
              Step {step + 1} of {steps.length} · Setup progress
            </div>
            <h2>{(steps[step] ?? steps[0])[0]}</h2>
            <p>{(steps[step] ?? steps[0])[1]}</p>
            {step === 0 && (
              <div className="form-grid">
                <Field label="Product name">
                  <input
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Customer Complaints"
                  />
                </Field>
                <Field label="Domain">
                  <input
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                    placeholder="e.g. Customer service"
                  />
                </Field>
                <div className="full-span">
                  <Field
                    label="Business purpose"
                    hint="Describe who will use this knowledge and what it helps them do."
                  >
                    <textarea
                      value={purpose}
                      onChange={(e) => setPurpose(e.target.value)}
                      placeholder="Help support teams answer customer questions with verified guidance."
                    />
                  </Field>
                </div>
                <Field label="Product owner">
                  <input
                    value={owner}
                    onChange={(e) => setOwner(e.target.value)}
                  />
                </Field>
              </div>
            )}
            {step === 1 && (
              <>
                <DataFiles items={files} setItems={setFiles} />
                <div className="intake-source">
                  <h3>
                    <Plug size={18} /> Connect or register a source
                  </h3>
                  <Field
                    label="Data source (optional)"
                    hint="Read a PostgreSQL table or HTTP API, or register any other location and use exported files."
                  >
                    <select
                      value={sourceId}
                      onChange={(e) => {
                        setSource(e.target.value);
                        setConnection(null);
                        setConnectionError(null);
                        setImportSourceNow(false);
                      }}
                    >
                      <option value="">Add sources later</option>
                      <option value="new">Add a new data source</option>
                      {sources?.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </Field>
                  {sourceId === "new" && (
                    <SourceFields
                      value={newSource}
                      onChange={(value) => {
                        setNewSource(value);
                        setConnection(null);
                        setConnectionError(null);
                      }}
                    />
                  )}
                  {liveSource && (
                    <>
                      <button
                        type="button"
                        disabled={testing}
                        onClick={() => void testSource()}
                      >
                        {testing
                          ? "Testing…"
                          : "Test connection and preview records"}
                      </button>
                      {connection && (
                        <div className="guidance">
                          {connection.record_count} records available.{" "}
                          {connection.message}
                        </div>
                      )}
                      {connectionError && (
                        <ErrorState message={connectionError} />
                      )}
                      <label className="checkbox-row">
                        <input
                          type="checkbox"
                          checked={importSourceNow}
                          onChange={(e) => setImportSourceNow(e.target.checked)}
                        />
                        Import a source snapshot when creating this draft
                      </label>
                      <p className="intake-note">
                        Leave this unchecked to save the source setup and import
                        later.
                      </p>
                    </>
                  )}
                  {sourceId && !liveSource && (
                    <p className="guidance">
                      The location will be saved. Files can be imported now;
                      this source does not have a live connection.
                    </p>
                  )}
                </div>
              </>
            )}
            {step === 2 && (
              <>
                <Field
                  label="Concept starter"
                  hint="Concepts give your documents a shared business meaning. Technical settings are prepared for you."
                >
                  <select
                    value={template}
                    onChange={(e) => setTemplate(e.target.value)}
                  >
                    <option value="general">
                      General knowledge — a simple starting point
                    </option>
                    <option value="customer-support">
                      Customer support — complaints and customers
                    </option>
                    <option value="empty">
                      Start empty — define concepts later
                    </option>
                  </select>
                </Field>
                <div className="guidance" style={{ marginTop: 20 }}>
                  You can add, rename, and explain concepts using plain-language
                  forms. Your team does not need to write technical definitions.
                </div>
              </>
            )}
            {step === 3 && (
              <>
                <div className="readiness-explainer">
                  <h3>Quality is checked after preparation</h3>
                  <p>
                    This step sets preferences. It does not measure how ready
                    your knowledge is yet.
                  </p>
                  <ul>
                    <li>Prepare your files and records.</li>
                    <li>Run quality checks and resolve findings.</li>
                    <li>Get reviewer approval before publishing.</li>
                  </ul>
                </div>
                <div className="form-grid">
                  <Field label="Quality requirements">
                    <select
                      value={strict ? "strict" : "flexible"}
                      onChange={(e) => setStrict(e.target.value === "strict")}
                    >
                      <option value="strict">
                        Complete product details — recommended
                      </option>
                      <option value="flexible">
                        Allow one missing product detail
                      </option>
                    </select>
                  </Field>
                  <Field
                    label="How many matching results?"
                    hint="The maximum evidence matches shown for each search. Fewer results keep the list focused."
                  >
                    <select
                      value={limit}
                      onChange={(e) => setLimit(Number(e.target.value))}
                    >
                      <option value={3}>Show up to 3 matching results</option>
                      <option value={5}>
                        Show up to 5 matching results — recommended
                      </option>
                      <option value={10}>Show up to 10 matching results</option>
                      <option value={20}>Show up to 20 matching results</option>
                    </select>
                  </Field>
                  <p className="full-span">
                    This is a search setting, not a readiness score.
                  </p>
                  <div className="full-span guidance">
                    A current quality check and reviewer approval are required
                    before publication. Documents, evidence, and business rules
                    remain required.
                  </div>
                </div>
              </>
            )}
            {step === 4 && (
              <>
                <dl className="detail-list">
                  <dt>Name</dt>
                  <dd>{name}</dd>
                  <dt>Purpose</dt>
                  <dd>{purpose || "Add later"}</dd>
                  <dt>Owner</dt>
                  <dd>{owner}</dd>
                  <dt>Files to import</dt>
                  <dd>
                    {files.length
                      ? files.map((item) => item.file.name).join(", ")
                      : "Add after creation"}
                  </dd>
                  <dt>Data source</dt>
                  <dd>
                    {sourceId === "new"
                      ? newSource.name
                      : chosenSource?.name || "Add later"}
                    {sourceId &&
                      (liveSource && importSourceNow
                        ? " · import snapshot now"
                        : " · setup saved, import later")}
                  </dd>
                  <dt>Search results</dt>
                  <dd>Up to {limit} evidence matches per search</dd>
                  <dt>Concept starter</dt>
                  <dd>
                    {template === "empty"
                      ? "Define later"
                      : template === "general"
                        ? "General knowledge"
                        : "Customer support"}
                  </dd>
                  <dt>Publication</dt>
                  <dd>
                    <Status value="draft" />
                  </dd>
                </dl>
                <div className="guidance">
                  Your draft is saved separately from published knowledge.
                  Connected apps keep using their current release until a new
                  version is approved and published.
                </div>
              </>
            )}
            <div className="form-actions">
              {step > 0 && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setStep(step - 1)}
                >
                  Back
                </button>
              )}
              <button
                className="primary"
                disabled={busy || testing || !name.trim() || fileErrors}
              >
                {busy ? "Creating…" : step === 4 ? "Create draft" : "Continue"}
              </button>
            </div>
          </form>
        </Block>
      </div>
    </>
  );
}
