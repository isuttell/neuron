import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { nodePolyfills } from "vite-plugin-node-polyfills";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  base: "/",
  plugins: [react(), nodePolyfills()],
  build: {
    sourcemap: mode === "development" ? "inline" : true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:5002",
      },
      "/static": {
        target: "http://localhost:5002",
      },
      "/ws": {
        target: "ws://localhost:5002",
        ws: true,
        rewriteWsOrigin: true,
      },
    },
  },
}));
