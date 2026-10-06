import { Link, useSearchParams } from "react-router-dom";
import { Plus, Archive, ArrowRight } from "lucide-react";
import { useData } from "../api/client";
import type { Catalog, OverviewData } from "../api/types";
import {
  Block,
  PageTitle,
  Field,
  Status,
  Empty,
  ErrorState,
  Loading,
} from "../components/shared";
import { ProductRows } from "./overview";
export function CatalogPage() {
  const [params, setParams] = useSearchParams();
  const { data, error, loading } = useData<Catalog>(
    "/products?" + params.toString(),
  );
  const { data: overview } = useData<OverviewData>("/overview");
  const change = (key: string, value: string) =>
    setParams((p) => {
      const n = new URLSearchParams(p);
      if (value) n.set(key, value);
      else n.delete(key);
      n.delete("offset");
      return n;
    });
  const products =
    data?.items.map((p) => ({
      ...p,
      ...overview?.products.find((item) => item.id === p.id),
    })) || [];
  return (
    <>
      <PageTitle
        eyebrow="KNOWLEDGE PRODUCTS"
        title="Knowledge products"
        description="Turn documents into trustworthy knowledge your teams and apps can use."
        action={
          <Link className="button primary" to="/products/new">
            <Plus size={16} />
            New knowledge product
          </Link>
        }
      />
      <div className="filters">
        <Field label="Search products">
          <input
            placeholder="Find a product…"
            value={params.get("q") || ""}
            onChange={(e) => change("q", e.target.value)}
          />
        </Field>
        <Field label="Publication filter">
          <select
            value={params.get("state") || ""}
            onChange={(e) => change("state", e.target.value)}
          >
            <option value="">All products</option>
            <option value="published">Has published release</option>
            <option value="draft">No published release</option>
          </select>
        </Field>
        <Field label="Domain filter">
          <input
            placeholder="All domains"
            value={params.get("domain") || ""}
            onChange={(e) => change("domain", e.target.value)}
          />
        </Field>
        <Field label="Owner filter">
          <input
            placeholder="All owners"
            value={params.get("owner") || ""}
            onChange={(e) => change("owner", e.target.value)}
          />
        </Field>
        <Field label="Sort products">
          <select
            value={params.get("sort") || "name"}
            onChange={(e) => change("sort", e.target.value)}
          >
            <option value="name">Name</option>
            <option value="recent">Recently created</option>
          </select>
        </Field>
      </div>
      {error && <ErrorState message={error} />}
      <div className="grid-4">
        {products.slice(0, 4).map((p) => (
          <Block key={p.id}>
            <Link
              to={"/products/" + p.id}
              className="block-body"
              style={{ display: "block", paddingTop: 22 }}
            >
              <div className="product-cell">
                <span className="round-icon">
                  <Archive />
                </span>
                <h3>{p.name}</h3>
              </div>
              <p style={{ fontSize: 11, margin: "15px 0", minHeight: 35 }}>
                {p.purpose || "Add a purpose to guide your team."}
              </p>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <Status
                  value={p.publication || p.draft?.state || "published"}
                />
                <ArrowRight size={15} />
              </div>
              <p style={{ fontSize: 10, marginTop: 14 }}>
                {p.domain} · {p.owner}
              </p>
            </Link>
          </Block>
        ))}
      </div>
      <div
        className="guidance"
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 20,
          alignItems: "center",
        }}
      >
        <div>
          <h3>Build a reliable knowledge product</h3>
          <p>
            Start with a purpose. Add documents, define concepts, then prepare
            and check.
          </p>
        </div>
        <Link className="button" to="/products/new">
          Start a draft <ArrowRight size={14} />
        </Link>
      </div>
      <Block
        title="Product catalog"
        subtitle={`${data?.total ?? 0} products · configuration and activity are saved`}
      >
        {loading ? (
          <Loading />
        ) : products.length ? (
          <ProductRows products={products} />
        ) : (
          <Empty
            title="No matching products"
            description="Adjust the filters or create a new knowledge product."
          />
        )}
      </Block>
      {data && data.total > 50 && (
        <div className="form-actions">
          <button
            disabled={(data.offset || 0) === 0}
            onClick={() =>
              setParams((p) => {
                p.set("offset", String(Math.max(0, data.offset - 50)));
                return p;
              })
            }
          >
            Previous
          </button>
          <button
            disabled={data.offset + 50 >= data.total}
            onClick={() =>
              setParams((p) => {
                p.set("offset", String(data.offset + 50));
                return p;
              })
            }
          >
            Next
          </button>
        </div>
      )}
    </>
  );
}
