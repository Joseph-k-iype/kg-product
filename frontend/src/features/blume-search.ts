import { api } from "../api/client";
import type { Catalog } from "../api/types";

// Blume's unused search hook still imports this virtual module during Vite resolution.
// Provide the real product catalog search contract rather than an Astro-only virtual client.
export async function createSearch() {
  return async (query: string) => {
    const catalog = await api<Catalog>(
      "/products?q=" + encodeURIComponent(query),
    );
    return {
      hits: catalog.items.map((product) => ({
        url: `/products/${product.id}/chat`,
        title: product.name,
        excerpt: product.purpose,
        content: product.purpose,
      })),
      sections: [],
    };
  };
}
