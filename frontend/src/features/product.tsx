import { createContext, useContext, useEffect, useState } from "react";
import { Link, NavLink, useParams, useNavigate } from "react-router-dom";
import { Archive, FileText, Boxes, ShieldCheck, Send } from "lucide-react";
import type { Product, Revision, OverviewData, Catalog } from "../api/types";
import { api, useData } from "../api/client";
import {
  PageTitle,
  Status,
  Block,
  Loading,
  ErrorState,
  NextLink,
  Field,
  Empty,
  useNotice,
} from "../components/shared";
import { DocumentsPage, ProcessingPage, SourcesPage } from "./documents";
import { ConceptsPage } from "./concepts";
import { ExplorerPage, LineagePage } from "./explore";
import { HealthPage, ReviewsPage, ReleasesPage } from "./governance";
import { RetrievalPage, ConsumersPage } from "./consume";
const ProductContext = createContext<{
  product: Product;
  revision: Revision;
  readonly: boolean;
} | null>(null);
export function useProduct() {
  const value = useContext(ProductContext);
  if (!value) throw new Error("Select a knowledge product");
  return value;
}
export function scoped(path: string) {
  const { product, revision } = useProduct();
  return (
    "/products/" +
    product.id +
    "/" +
    path +
    (path.includes("?") ? "&" : "?") +
    "revision_id=" +
    revision.id
  );
}
const tabs = [
  ["overview", "Overview"],
  ["sources", "Documents"],
  ["concepts", "Concepts & Rules"],
  ["explorer", "Explore Knowledge"],
  ["processing", "Prepare Knowledge"],
  ["health", "Quality Checks"],
  ["reviews", "Approvals"],
  ["retrieval", "Search"],
  ["lineage", "Evidence Trail"],
  ["consumers", "Connected Apps"],
  ["releases", "Release Activity"],
];
export function Workspace({
  id: propId,
  tab: propTab,
}: {
  id?: string;
  tab?: string;
}) {
  const params = useParams();
  const id = propId || params.id;
  const tab = propTab || params.tab || "overview";
  const { data, error, loading } = useData<Product>(
    id ? "/products/" + id : null,
  );
  const [selected, setSelected] = useState("");
  const { busy, run } = useNotice();
  useEffect(() => {
    if (id) sessionStorage.setItem("currentProduct", id);
    setSelected("");
  }, [id]);
  if (loading) return <Loading />;
  if (error || !data)
    return <ErrorState message={error || "Product unavailable"} />;
  const rev =
    data.revisions.find((r) => r.id === selected) ||
    data.draft ||
    data.revisions[0];
  const readonly = rev.state === "published";
  const pages: Record<string, React.ReactNode> = {
    overview: <ProductOverview />,
    sources: <DocumentsPage />,
    concepts: <ConceptsPage />,
    explorer: <ExplorerPage />,
    processing: <ProcessingPage />,
    health: <HealthPage />,
    reviews: <ReviewsPage />,
    retrieval: <RetrievalPage />,
    lineage: <LineagePage />,
    consumers: <ConsumersPage />,
    releases: <ReleasesPage />,
  };
  return (
    <ProductContext.Provider value={{ product: data, revision: rev, readonly }}>
      <PageTitle
        eyebrow="KNOWLEDGE PRODUCT"
        title={data.name}
        description={
          data.purpose ||
          "Add a business purpose so your team knows how to use this knowledge."
        }
        action={
          readonly ? (
            <button
              className="primary"
              disabled={busy}
              onClick={() =>
                run("Draft opened", async () => {
                  await api("/products/" + id + "/draft", "POST");
                  setSelected("");
                })
              }
            >
              Open a draft
            </button>
          ) : (
            <Link
              className="button primary"
              to={"/products/" + id + "/processing"}
            >
              Prepare knowledge
            </Link>
          )
        }
      />
      <div className="product-meta">
        <div>
          <small>Owner</small>
          <span>{data.owner}</span>
        </div>
        <div>
          <small>Product lifecycle</small>
          <span aria-label="Product lifecycle">
            <Status value={data.active_release_id ? "active" : "draft"} />
          </span>
        </div>
        <div>
          <small>Current version</small>
          <Status
            value={rev.state}
            label={
              (readonly ? "Published" : "Draft") + " revision " + rev.number
            }
          />
        </div>
        <div>
          <small>Published release</small>
          <span>
            {data.active_release_id
              ? "Available to connected apps"
              : "Not published yet"}
          </span>
        </div>
        <Field label="Version to inspect">
          <select value={rev.id} onChange={(e) => setSelected(e.target.value)}>
            {data.revisions.map((r) => (
              <option value={r.id} key={r.id}>
                {r.state === "published" ? "Published" : "Draft"} revision{" "}
                {r.number}
              </option>
            ))}
          </select>
        </Field>
      </div>
      {readonly && (
        <div className="guidance">
          You are viewing an immutable published version. Open a draft to make
          changes; connected apps continue using the published release.
        </div>
      )}
      <nav className="tabs" aria-label="Product sections">
        {tabs.map(([key, label]) => (
          <NavLink
            key={key}
            to={"/products/" + id + "/" + key}
            className={tab === key ? "active" : ""}
          >
            {label}
          </NavLink>
        ))}
      </nav>
      {pages[tab] || <ProductOverview />}
    </ProductContext.Provider>
  );
}
function ProductOverview() {
  const { product, revision, readonly } = useProduct();
  const { data } = useData<OverviewData>("/overview");
  const { busy, run } = useNotice();
  const [editing, setEditing] = useState(false),
    [name, setName] = useState(product.name),
    [purpose, setPurpose] = useState(product.purpose),
    [owner, setOwner] = useState(product.owner);
  const summary = data?.products.find((p) => p.id === product.id);
  const items = [
    [
      "Documents",
      FileText,
      `${summary?.documents_ready || 0} of ${summary?.documents_total || 0} ready`,
      "Add documents",
      "sources",
    ],
    [
      "Concepts & Rules",
      Boxes,
      revision.ontology_id
        ? "Definitions saved"
        : "Choose a starter or define concepts",
      "Review concepts",
      "concepts",
    ],
    [
      "Prepare Knowledge",
      Archive,
      summary?.processing === "ready"
        ? "Documents searchable"
        : "Prepare documents and supported facts",
      "Prepare knowledge",
      "processing",
    ],
    [
      "Quality Checks",
      ShieldCheck,
      summary?.quality === "passed"
        ? "Current checks passed"
        : "Run checks to assess readiness",
      "Run checks",
      "health",
    ],
    [
      "Reviewer Approval",
      Send,
      revision.state === "approved"
        ? "Approved"
        : readonly
          ? "Published"
          : "Request approval when checks pass",
      "Request approval",
      "reviews",
    ],
  ] as const;
  return (
    <div className="grid-2">
      <Block
        title="Your readiness checklist"
        subtitle="A clear next step at every stage."
      >
        {items.map(([title, Icon, description, action, to]) => (
          <div className="checklist-row" key={title}>
            <span className="round-icon">
              <Icon />
            </span>
            <div>
              <h3>{title}</h3>
              <p>{description}</p>
            </div>
            <NextLink to={"/products/" + product.id + "/" + to}>
              {action}
            </NextLink>
          </div>
        ))}
      </Block>
      <div>
        <Block
          title="Product details"
          action={
            !readonly && (
              <button onClick={() => setEditing((v) => !v)}>
                {editing ? "Cancel" : "Edit"}
              </button>
            )
          }
        >
          {editing ? (
            <form
              className="block-body"
              onSubmit={(e) => {
                e.preventDefault();
                run("Product details saved", async () => {
                  await api("/products/" + product.id, "PATCH", {
                    expected_generation: revision.generation,
                    name,
                    purpose,
                    owner,
                  });
                  setEditing(false);
                });
              }}
            >
              <Field label="Product name">
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field label="Business purpose">
                <textarea
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                />
              </Field>
              <Field label="Product owner">
                <input
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                />
              </Field>
              <div className="form-actions">
                <button className="primary" disabled={busy}>
                  Save details
                </button>
              </div>
            </form>
          ) : (
            <dl className="detail-list">
              <dt>Domain</dt>
              <dd>{product.domain}</dd>
              <dt>Owner</dt>
              <dd>{product.owner}</dd>
              <dt>Lifecycle</dt>
              <dd>
                <Status value={summary?.lifecycle || "draft"} />
              </dd>
              <dt>Processing</dt>
              <dd>
                <Status value={summary?.processing || "needs_preparation"} />
              </dd>
              <dt>Quality</dt>
              <dd>
                <Status value={summary?.quality || "not_checked"} />
              </dd>
              <dt>Publication</dt>
              <dd>
                <Status value={revision.state} />
              </dd>
            </dl>
          )}
        </Block>
        <div className="guidance">
          <h3>What is a knowledge product?</h3>
          <p>
            A collection of documents, shared concepts, and verified facts that
            your team can trust and your apps can search.
          </p>
        </div>
      </div>
    </div>
  );
}
export function ContextPage({ tab }: { tab: string }) {
  const { data, loading, error } = useData<Catalog>("/products");
  const [id, setId] = useState(sessionStorage.getItem("currentProduct") || "");
  useEffect(() => {
    if (data && !data.items.some((p) => p.id === id))
      setId(data.items[0]?.id || "");
  }, [data, id]);
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;
  if (!id)
    return (
      <>
        <PageTitle
          title={tabs.find(([key]) => key === tab)?.[1] || "Knowledge"}
          description="Choose a knowledge product to start."
        />
        <Empty
          title="Create your first product"
          description="These tools work within a product and its version."
          action={
            <Link className="button primary" to="/products/new">
              New knowledge product
            </Link>
          }
        />
      </>
    );
  return (
    <>
      <div className="filters">
        <Field label="Knowledge product">
          <select
            value={id}
            onChange={(e) => {
              setId(e.target.value);
              sessionStorage.setItem("currentProduct", e.target.value);
            }}
          >
            {data?.items.map((p) => (
              <option value={p.id} key={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Workspace id={id} tab={tab} />
    </>
  );
}
export function SourceRegistry() {
  return <SourcesPage />;
}
