import { createContext, useContext } from "react";
import type { Product, Revision } from "@/api/types";

export const ProductContext = createContext<{
  product: Product;
  revision: Revision;
  readonly: boolean;
} | null>(null);
export function useProduct() {
  const value = useContext(ProductContext);
  if (!value) throw new Error("Select a knowledge product");
  return value;
}
export function useScopedPath(path: string) {
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
