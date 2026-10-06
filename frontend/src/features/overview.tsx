import { Link } from "react-router-dom";
import {
  Archive,
  Clock,
  TriangleAlert,
  FileText,
  Plus,
  CheckCircle2,
} from "lucide-react";
import { useData } from "../api/client";
import type { OverviewData, Product } from "../api/types";
import { KnowledgeSignal } from "../components/KnowledgeSignal";
import {
  Block,
  PageTitle,
  Status,
  Loading,
  ErrorState,
  Empty,
  date,
  NextLink,
} from "../components/shared";
export function ProductRows({ products }: { products: Product[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Product</th>
            <th>Owner</th>
            <th>Documents ready</th>
            <th>Quality checks</th>
            <th>Publication</th>
            <th>
              <span className="sr-only">Open product</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {products.map((p) => (
            <tr key={p.id}>
              <td>
                <Link to={"/products/" + p.id} className="product-cell">
                  <span className="round-icon">
                    <Archive />
                  </span>
                  <strong>{p.name}</strong>
                </Link>
              </td>
              <td>
                <span className="owner-cell">
                  <span className="avatar">
                    {p.owner
                      .split(" ")
                      .map((s) => s[0])
                      .slice(0, 2)
                      .join("")}
                  </span>
                  {p.owner}
                </span>
              </td>
              <td>
                {p.documents_ready ?? 0} / {p.documents_total ?? 0}
                <div className="progress-track">
                  <span
                    style={{
                      width:
                        (p.documents_total
                          ? ((p.documents_ready || 0) / p.documents_total) * 100
                          : 0) + "%",
                    }}
                  />
                </div>
              </td>
              <td>
                <Status value={p.quality || "not_checked"} />
              </td>
              <td>
                <Status
                  value={p.publication || p.draft?.state || "published"}
                />
              </td>
              <td>
                <NextLink to={"/products/" + p.id}>Open</NextLink>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Overview() {
  const { data, error, loading } = useData<OverviewData>("/overview", 10000);
  if (loading) return <Loading />;
  if (error || !data)
    return <ErrorState message={error || "Unable to load overview"} />;
  const metrics = [
    [
      "Active products",
      data.summary.active_products,
      Archive,
      "Published knowledge",
    ],
    [
      "Awaiting approval",
      data.summary.pending_reviews,
      Clock,
      "Ready for a reviewer",
    ],
    [
      "Blocked releases",
      data.summary.blocked_releases,
      TriangleAlert,
      "Checks need attention",
    ],
    [
      "Overdue sources",
      data.summary.overdue_sources,
      FileText,
      "Keep your documents current",
    ],
  ] as const;
  return (
    <>
      <div className="overview-hero">
        <KnowledgeSignal />
        <PageTitle
          eyebrow="KNOWLEDGE PLATFORM"
          title="Your knowledge, ready to use."
          description="Keep documents current, check quality, and publish with confidence."
          action={
            <Link className="button primary" to="/products/new">
              <Plus size={16} />
              New knowledge product
            </Link>
          }
        />
      </div>
      <div className="metrics">
        {metrics.map(([label, value, Icon, help], index) => (
          <div className="metric-block" key={label}>
            <span className="metric-index" aria-hidden="true">
              0{index + 1}
            </span>
            <Icon />
            <div>
              <div className="metric-label">{label}</div>
              <div className="metric-number">{value}</div>
              <small>{help}</small>
            </div>
          </div>
        ))}
      </div>
      <Block
        title="Attention queue"
        subtitle="Your next steps to keep knowledge accurate and ready to use."
        action={<NextLink to="/products">All products</NextLink>}
      >
        {data.attention.length ? (
          <div className="attention-list">
            {data.attention.slice(0, 4).map((a) => (
              <div className="attention-row" key={a.id}>
                <span className={"severity " + a.severity}>
                  {a.severity === "high"
                    ? "● High"
                    : a.severity === "medium"
                      ? "● Medium"
                      : "● Low"}
                </span>
                <div>
                  <strong>{a.product_name}</strong>
                  <p>{a.issue}</p>
                </div>
                <Status
                  value={
                    a.severity === "high"
                      ? "failed"
                      : a.severity === "medium"
                        ? "needs_preparation"
                        : "ready"
                  }
                  label={
                    a.severity === "high"
                      ? "Needs attention"
                      : a.severity === "medium"
                        ? "Action needed"
                        : "Next step"
                  }
                />
                <Link className="button" to={a.url}>
                  {a.action}
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <Empty
            title="Everything is up to date"
            description="No outstanding preparation or review tasks."
            action={<CheckCircle2 size={22} />}
          />
        )}
      </Block>
      <div className="grid-2">
        <Block
          title="Product readiness"
          subtitle="A clear view of documents, checks, and publication."
          action={<NextLink to="/products">View all</NextLink>}
        >
          {data.products.length ? (
            <ProductRows products={data.products.slice(0, 6)} />
          ) : (
            <Empty
              title="Create your first knowledge product"
              description="Bring documents together around a business purpose."
            />
          )}
        </Block>
        <Block
          title="Recent publications"
          subtitle="Verified versions available to your connected apps."
        >
          {data.publications.length ? (
            data.publications.map((r) => (
              <div className="publication-row" key={r.id}>
                <div>
                  <Link to={"/products/" + r.product_id + "/releases"}>
                    {r.product_name}
                  </Link>
                  <p>
                    Release {r.number} · {date(r.created_at)}
                  </p>
                </div>
                <Status value="published" />
              </div>
            ))
          ) : (
            <Empty
              title="Your first release starts here"
              description="Prepare a draft, run checks, and get approval before publishing."
            />
          )}
        </Block>
      </div>
      <p className="content-note">
        Local demo workspace · Synthetic identities and documents · Every action
        is saved.
      </p>
    </>
  );
}
