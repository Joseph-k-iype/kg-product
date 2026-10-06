import { fileURLToPath, URL } from "node:url";

export const aliases = {
  "@": fileURLToPath(new URL("../src", import.meta.url)),
  "blume:search-client": fileURLToPath(
    new URL("../src/features/blume-search.ts", import.meta.url),
  ),
};
