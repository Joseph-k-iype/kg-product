import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { aliases } from "./tooling/paths";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: aliases, dedupe: ["react", "react-dom"] },
  test: {
    environment: "jsdom",
    include: ["src/test/**/*.test.{ts,tsx}"],
    restoreMocks: true,
    clearMocks: true,
  },
});
