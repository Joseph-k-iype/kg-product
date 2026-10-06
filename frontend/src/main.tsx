import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Shell } from "./components/Shell";
import {
  NoticeProvider,
  PageTitle,
  Block,
  Status,
  ErrorState,
  Loading,
} from "./components/shared";
import { Overview } from "./features/overview";
import { CatalogPage } from "./features/catalog";
import { CreateProduct } from "./features/create";
import { Workspace, ContextPage, SourceRegistry } from "./features/product";
import { useData } from "./api/client";
import "./style.css";
function Operations() {
  const { data, error, loading } = useData<{
    probes: Record<string, string>;
    identity_mode: string;
  }>("/health", 5000);
  return (
    <>
      <PageTitle
        eyebrow="OPERATIONS"
        title="Service status"
        description="Technical details for workspace administrators."
      />
      <Block title="Local services">
        {error ? (
          <ErrorState message={error} />
        ) : loading ? (
          <Loading />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Connection</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data?.probes || {}).map(([name, state]) => (
                  <tr key={name}>
                    <td>
                      {name === "postgres"
                        ? "PostgreSQL with pgvector"
                        : name === "minio"
                          ? "MinIO object storage"
                          : "FalkorDB instance storage"}
                    </td>
                    <td>
                      <Status
                        value={state === "ready" ? "ready" : "failed"}
                        label={state}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Block>
      <div className="guidance">
        This local application uses synthetic identities. It does not implement
        production authentication. RDF definitions are stored as versioned
        files; unrestricted reasoning and a remote SPARQL endpoint are not
        enabled.
      </div>
    </>
  );
}
function App() {
  return (
    <BrowserRouter>
      <NoticeProvider>
        <Shell>
          <Routes>
            <Route path="/" element={<Navigate to="/overview" replace />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/products" element={<CatalogPage />} />
            <Route path="/products/new" element={<CreateProduct />} />
            <Route path="/products/:id/:tab?" element={<Workspace />} />
            <Route path="/sources" element={<SourceRegistry />} />
            {[
              "concepts",
              "explorer",
              "health",
              "reviews",
              "retrieval",
              "lineage",
              "consumers",
            ].map((tab) => (
              <Route
                key={tab}
                path={"/" + tab}
                element={<ContextPage tab={tab} />}
              />
            ))}
            <Route path="/operations" element={<Operations />} />
            <Route path="*" element={<Navigate to="/overview" replace />} />
          </Routes>
        </Shell>
      </NoticeProvider>
    </BrowserRouter>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
