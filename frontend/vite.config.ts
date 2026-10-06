import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { aliases } from "./tooling/paths";
export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ["react", "react-dom"],
    alias: aliases,
  },
  server: {
    proxy: { "/api": process.env.API_URL || "http://127.0.0.1:58000" },
  },
});
