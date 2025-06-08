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
    outDir: path.resolve(__dirname, "src/neuron_client/dist"),
  },
  root: "src/neuron_client",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src/neuron_client/src"),
    },
  },
  server: {
    port: 5174,
    proxy: {
      "/api": {
        target: "http://localhost:5003",
      },
      "/static": {
        target: "http://localhost:5003",
      },
      "/logo.svg": {
        target: "http://localhost:5003",
      },
      "/ws": {
        target: "ws://localhost:5003",
        ws: true,
        rewriteWsOrigin: true,
      },
    },
  },
}));
