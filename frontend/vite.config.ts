import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ["react", "react-dom"],
    alias: {
      "blume:search-client": fileURLToPath(
        new URL("./src/features/blume-search.ts", import.meta.url),
      ),
    },
  },
  server: {
    proxy: { "/api": process.env.API_URL || "http://127.0.0.1:58000" },
  },
});
