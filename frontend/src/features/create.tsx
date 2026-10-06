import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Check, FileUp } from "lucide-react";
import { api } from "../api/client";
import type { Product, Source } from "../api/types";
import { useData } from "../api/client";
import {
  PageTitle,
  Block,
  Field,
  useNotice,
  Status,
} from "../components/shared";
const steps = [
  ["Purpose", "Define the goal and ownership"],
  ["Documents", "Choose the evidence to use"],
  ["Concepts", "Choose a simple starting point"],
  ["Readiness", "Set checks and search defaults"],
  ["Summary", "Review and create a draft"],
];
export function CreateProduct() {
  const [step, setStep] = useState(0),
    [name, setName] = useState(""),
    [purpose, setPurpose] = useState(""),
    [domain, setDomain] = useState("General"),
    [owner, setOwner] = useState("Maya Chen"),
    [file, setFile] = useState<File | null>(null),
    [sourceId, setSource] = useState(""),
    [template, setTemplate] = useState("general"),
    [strict, setStrict] = useState(true),
    [limit, setLimit] = useState(5);
  const { data: sources } = useData<Source[]>("/sources");
  const { busy, run } = useNotice();
  const navigate = useNavigate();
  const create = () =>
    run("Draft created", async () => {
      const p = await api<Product>("/products", "POST", {
        name,
        purpose,
        domain,
        owner,
        config: { quality_gates: strict ? {} : { metadata: 0.75 }, limit },
      });
      sessionStorage.setItem("currentProduct", p.id);
      try {
        if (template !== "empty")
          await api("/products/" + p.id + "/ontology/starter", "POST", {
            template,
          });
        if (sourceId) {
          const source = sources?.find((s) => s.id === sourceId);
          if (source)
            await api<Source>("/sources", "POST", {
              name: source.name + " scope for " + name,
              type: source.type,
              owner: source.owner,
              location: source.location,
              freshness_days: source.freshness_days,
              product_ids: [p.id],
            });
        }
        if (file) {
          const form = new FormData();
          form.append("file", file);
          await api("/products/" + p.id + "/documents", "POST", form);
        }
      } finally {
        navigate("/products/" + p.id);
      }
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
            <h2>{steps[step][0]}</h2>
            <p>{steps[step][1]}</p>
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
                <div className="upload-area">
                  <FileUp size={25} />
                  <Field
                    label="Add a document"
                    hint="PDF, Word, text or Markdown · up to 20 MB · optional for now"
                  >
                    <input
                      type="file"
                      accept=".pdf,.docx,.txt,.md"
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                    />
                  </Field>
                </div>
                <Field
                  label="Existing source to register"
                  hint="Registers the source location; external sources are not connected automatically."
                >
                  <select
                    value={sourceId}
                    onChange={(e) => setSource(e.target.value)}
                  >
                    <option value="">Add sources later</option>
                    {sources?.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </Field>
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
              <div className="form-grid">
                <Field label="Quality requirements">
                  <select
                    value={strict ? "strict" : "flexible"}
                    onChange={(e) => setStrict(e.target.value === "strict")}
                  >
                    <option value="strict">All checks must pass</option>
                    <option value="flexible">
                      Allow incomplete product details
                    </option>
                  </select>
                </Field>
                <Field label="Search result limit">
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                  />
                </Field>
                <div className="full-span guidance">
                  A current quality check and reviewer approval are required
                  before publication. Documents, evidence, and business rules
                  remain required.
                </div>
              </div>
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
                  <dt>Documents</dt>
                  <dd>{file?.name || "Add after creation"}</dd>
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
              <button className="primary" disabled={busy || !name.trim()}>
                {busy ? "Creating…" : step === 4 ? "Create draft" : "Continue"}
              </button>
            </div>
          </form>
        </Block>
      </div>
    </>
  );
}
