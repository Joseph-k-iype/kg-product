import { Routes, Route, Navigate } from "react-router-dom";
import { Shell } from "@/components/Shell";
import { Overview } from "@/features/overview";
import { CatalogPage } from "@/features/catalog";
import { CreateProduct } from "@/features/create";
import { Workspace, ContextPage, SourceRegistry } from "@/features/product";
import { Operations } from "@/features/operations";
import { AppProviders } from "./providers";

export function App() {
  return (
    <AppProviders>
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
            "chat",
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
    </AppProviders>
  );
}
