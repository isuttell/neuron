// vitest.config.ts
import { mergeConfig } from "file:///home/isuttell/src/neuron/node_modules/vite/dist/node/index.js";
import { defineConfig as defineVitestConfig } from "file:///home/isuttell/src/neuron/node_modules/vitest/dist/config.js";

// vite.config.ts
import { defineConfig } from "file:///home/isuttell/src/neuron/node_modules/vite/dist/node/index.js";
import react from "file:///home/isuttell/src/neuron/node_modules/@vitejs/plugin-react/dist/index.mjs";
import { nodePolyfills } from "file:///home/isuttell/src/neuron/node_modules/vite-plugin-node-polyfills/dist/index.js";
import path from "path";
var __vite_injected_original_dirname = "/home/isuttell/src/neuron";
var vite_config_default = defineConfig(({ mode }) => ({
  base: "/",
  plugins: [react(), nodePolyfills()],
  build: {
    sourcemap: mode === "development" ? "inline" : true,
    outDir: path.resolve(__vite_injected_original_dirname, "src/neuron_client/dist"),
    manifest: true
  },
  root: "src/neuron_client",
  resolve: {
    alias: {
      "@": path.resolve(__vite_injected_original_dirname, "src/neuron_client/src")
    }
  },
  server: {
    port: 5176,
    proxy: {
      "/api": {
        target: "http://localhost:5000"
      },
      "/static": {
        target: "http://localhost:5000"
      },
      "/logo.svg": {
        target: "http://localhost:5000"
      },
      "/ws": {
        target: "ws://localhost:5000",
        ws: true,
        rewriteWsOrigin: true
      }
    }
  }
}));

// vitest.config.ts
var vitest_config_default = mergeConfig(
  vite_config_default({ mode: "test" }),
  defineVitestConfig({
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["../../test/setupTests.ts"],
      coverage: {
        provider: "v8",
        reporter: ["text", "json", "html"],
        exclude: [
          "node_modules/",
          "src/neuron_client/src/components/ui/**",
          "src/neuron_client/src/vite-env.d.ts",
          "src/neuron_client/src/main.tsx",
          "src/neuron_client/src/lib/utils.ts",
          "src/neuron_client/src/**/*.stories.{ts,tsx}",
          "src/neuron_client/dist/**",
          "**/*.d.ts",
          "**/*.config.*",
          "**/mockData.ts",
          "test/**"
        ]
      },
      css: {
        modules: {
          classNameStrategy: "non-scoped"
        }
      },
      pool: "threads",
      poolOptions: {
        threads: {
          singleThread: false
        }
      }
    }
  })
);
export {
  vitest_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZXN0LmNvbmZpZy50cyIsICJ2aXRlLmNvbmZpZy50cyJdLAogICJzb3VyY2VzQ29udGVudCI6IFsiY29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2Rpcm5hbWUgPSBcIi9ob21lL2lzdXR0ZWxsL3NyYy9uZXVyb25cIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIi9ob21lL2lzdXR0ZWxsL3NyYy9uZXVyb24vdml0ZXN0LmNvbmZpZy50c1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vaG9tZS9pc3V0dGVsbC9zcmMvbmV1cm9uL3ZpdGVzdC5jb25maWcudHNcIjtpbXBvcnQgeyBkZWZpbmVDb25maWcsIG1lcmdlQ29uZmlnIH0gZnJvbSBcInZpdGVcIjtcbmltcG9ydCB7IGRlZmluZUNvbmZpZyBhcyBkZWZpbmVWaXRlc3RDb25maWcgfSBmcm9tIFwidml0ZXN0L2NvbmZpZ1wiO1xuaW1wb3J0IHZpdGVDb25maWcgZnJvbSBcIi4vdml0ZS5jb25maWdcIjtcblxuZXhwb3J0IGRlZmF1bHQgbWVyZ2VDb25maWcoXG4gIHZpdGVDb25maWcoeyBtb2RlOiBcInRlc3RcIiB9KSxcbiAgZGVmaW5lVml0ZXN0Q29uZmlnKHtcbiAgICB0ZXN0OiB7XG4gICAgICBnbG9iYWxzOiB0cnVlLFxuICAgICAgZW52aXJvbm1lbnQ6IFwianNkb21cIixcbiAgICAgIHNldHVwRmlsZXM6IFtcIi4uLy4uL3Rlc3Qvc2V0dXBUZXN0cy50c1wiXSxcbiAgICAgIGNvdmVyYWdlOiB7XG4gICAgICAgIHByb3ZpZGVyOiBcInY4XCIsXG4gICAgICAgIHJlcG9ydGVyOiBbXCJ0ZXh0XCIsIFwianNvblwiLCBcImh0bWxcIl0sXG4gICAgICAgIGV4Y2x1ZGU6IFtcbiAgICAgICAgICBcIm5vZGVfbW9kdWxlcy9cIixcbiAgICAgICAgICBcInNyYy9uZXVyb25fY2xpZW50L3NyYy9jb21wb25lbnRzL3VpLyoqXCIsXG4gICAgICAgICAgXCJzcmMvbmV1cm9uX2NsaWVudC9zcmMvdml0ZS1lbnYuZC50c1wiLFxuICAgICAgICAgIFwic3JjL25ldXJvbl9jbGllbnQvc3JjL21haW4udHN4XCIsXG4gICAgICAgICAgXCJzcmMvbmV1cm9uX2NsaWVudC9zcmMvbGliL3V0aWxzLnRzXCIsXG4gICAgICAgICAgXCJzcmMvbmV1cm9uX2NsaWVudC9zcmMvKiovKi5zdG9yaWVzLnt0cyx0c3h9XCIsXG4gICAgICAgICAgXCJzcmMvbmV1cm9uX2NsaWVudC9kaXN0LyoqXCIsXG4gICAgICAgICAgXCIqKi8qLmQudHNcIixcbiAgICAgICAgICBcIioqLyouY29uZmlnLipcIixcbiAgICAgICAgICBcIioqL21vY2tEYXRhLnRzXCIsXG4gICAgICAgICAgXCJ0ZXN0LyoqXCIsXG4gICAgICAgIF0sXG4gICAgICB9LFxuICAgICAgY3NzOiB7XG4gICAgICAgIG1vZHVsZXM6IHtcbiAgICAgICAgICBjbGFzc05hbWVTdHJhdGVneTogXCJub24tc2NvcGVkXCIsXG4gICAgICAgIH0sXG4gICAgICB9LFxuICAgICAgcG9vbDogXCJ0aHJlYWRzXCIsXG4gICAgICBwb29sT3B0aW9uczoge1xuICAgICAgICB0aHJlYWRzOiB7XG4gICAgICAgICAgc2luZ2xlVGhyZWFkOiBmYWxzZSxcbiAgICAgICAgfSxcbiAgICAgIH0sXG4gICAgfSxcbiAgfSlcbik7XG4iLCAiY29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2Rpcm5hbWUgPSBcIi9ob21lL2lzdXR0ZWxsL3NyYy9uZXVyb25cIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIi9ob21lL2lzdXR0ZWxsL3NyYy9uZXVyb24vdml0ZS5jb25maWcudHNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL2hvbWUvaXN1dHRlbGwvc3JjL25ldXJvbi92aXRlLmNvbmZpZy50c1wiO2ltcG9ydCB7IGRlZmluZUNvbmZpZyB9IGZyb20gXCJ2aXRlXCI7XG5pbXBvcnQgcmVhY3QgZnJvbSBcIkB2aXRlanMvcGx1Z2luLXJlYWN0XCI7XG5pbXBvcnQgeyBub2RlUG9seWZpbGxzIH0gZnJvbSBcInZpdGUtcGx1Z2luLW5vZGUtcG9seWZpbGxzXCI7XG5pbXBvcnQgcGF0aCBmcm9tIFwicGF0aFwiO1xuXG4vLyBodHRwczovL3ZpdGVqcy5kZXYvY29uZmlnL1xuZXhwb3J0IGRlZmF1bHQgZGVmaW5lQ29uZmlnKCh7IG1vZGUgfSkgPT4gKHtcbiAgYmFzZTogXCIvXCIsXG4gIHBsdWdpbnM6IFtyZWFjdCgpLCBub2RlUG9seWZpbGxzKCldLFxuICBidWlsZDoge1xuICAgIHNvdXJjZW1hcDogbW9kZSA9PT0gXCJkZXZlbG9wbWVudFwiID8gXCJpbmxpbmVcIiA6IHRydWUsXG4gICAgb3V0RGlyOiBwYXRoLnJlc29sdmUoX19kaXJuYW1lLCBcInNyYy9uZXVyb25fY2xpZW50L2Rpc3RcIiksXG4gICAgbWFuaWZlc3Q6IHRydWUsXG4gIH0sXG4gIHJvb3Q6IFwic3JjL25ldXJvbl9jbGllbnRcIixcbiAgcmVzb2x2ZToge1xuICAgIGFsaWFzOiB7XG4gICAgICBcIkBcIjogcGF0aC5yZXNvbHZlKF9fZGlybmFtZSwgXCJzcmMvbmV1cm9uX2NsaWVudC9zcmNcIiksXG4gICAgfSxcbiAgfSxcbiAgc2VydmVyOiB7XG4gICAgcG9ydDogNTE3NixcbiAgICBwcm94eToge1xuICAgICAgXCIvYXBpXCI6IHtcbiAgICAgICAgdGFyZ2V0OiBcImh0dHA6Ly9sb2NhbGhvc3Q6NTAwMFwiLFxuICAgICAgfSxcbiAgICAgIFwiL3N0YXRpY1wiOiB7XG4gICAgICAgIHRhcmdldDogXCJodHRwOi8vbG9jYWxob3N0OjUwMDBcIixcbiAgICAgIH0sXG4gICAgICBcIi9sb2dvLnN2Z1wiOiB7XG4gICAgICAgIHRhcmdldDogXCJodHRwOi8vbG9jYWxob3N0OjUwMDBcIixcbiAgICAgIH0sXG4gICAgICBcIi93c1wiOiB7XG4gICAgICAgIHRhcmdldDogXCJ3czovL2xvY2FsaG9zdDo1MDAwXCIsXG4gICAgICAgIHdzOiB0cnVlLFxuICAgICAgICByZXdyaXRlV3NPcmlnaW46IHRydWUsXG4gICAgICB9LFxuICAgIH0sXG4gIH0sXG59KSk7XG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQWlRLFNBQXVCLG1CQUFtQjtBQUMzUyxTQUFTLGdCQUFnQiwwQkFBMEI7OztBQ0QwTSxTQUFTLG9CQUFvQjtBQUMxUixPQUFPLFdBQVc7QUFDbEIsU0FBUyxxQkFBcUI7QUFDOUIsT0FBTyxVQUFVO0FBSGpCLElBQU0sbUNBQW1DO0FBTXpDLElBQU8sc0JBQVEsYUFBYSxDQUFDLEVBQUUsS0FBSyxPQUFPO0FBQUEsRUFDekMsTUFBTTtBQUFBLEVBQ04sU0FBUyxDQUFDLE1BQU0sR0FBRyxjQUFjLENBQUM7QUFBQSxFQUNsQyxPQUFPO0FBQUEsSUFDTCxXQUFXLFNBQVMsZ0JBQWdCLFdBQVc7QUFBQSxJQUMvQyxRQUFRLEtBQUssUUFBUSxrQ0FBVyx3QkFBd0I7QUFBQSxJQUN4RCxVQUFVO0FBQUEsRUFDWjtBQUFBLEVBQ0EsTUFBTTtBQUFBLEVBQ04sU0FBUztBQUFBLElBQ1AsT0FBTztBQUFBLE1BQ0wsS0FBSyxLQUFLLFFBQVEsa0NBQVcsdUJBQXVCO0FBQUEsSUFDdEQ7QUFBQSxFQUNGO0FBQUEsRUFDQSxRQUFRO0FBQUEsSUFDTixNQUFNO0FBQUEsSUFDTixPQUFPO0FBQUEsTUFDTCxRQUFRO0FBQUEsUUFDTixRQUFRO0FBQUEsTUFDVjtBQUFBLE1BQ0EsV0FBVztBQUFBLFFBQ1QsUUFBUTtBQUFBLE1BQ1Y7QUFBQSxNQUNBLGFBQWE7QUFBQSxRQUNYLFFBQVE7QUFBQSxNQUNWO0FBQUEsTUFDQSxPQUFPO0FBQUEsUUFDTCxRQUFRO0FBQUEsUUFDUixJQUFJO0FBQUEsUUFDSixpQkFBaUI7QUFBQSxNQUNuQjtBQUFBLElBQ0Y7QUFBQSxFQUNGO0FBQ0YsRUFBRTs7O0FEbkNGLElBQU8sd0JBQVE7QUFBQSxFQUNiLG9CQUFXLEVBQUUsTUFBTSxPQUFPLENBQUM7QUFBQSxFQUMzQixtQkFBbUI7QUFBQSxJQUNqQixNQUFNO0FBQUEsTUFDSixTQUFTO0FBQUEsTUFDVCxhQUFhO0FBQUEsTUFDYixZQUFZLENBQUMsMEJBQTBCO0FBQUEsTUFDdkMsVUFBVTtBQUFBLFFBQ1IsVUFBVTtBQUFBLFFBQ1YsVUFBVSxDQUFDLFFBQVEsUUFBUSxNQUFNO0FBQUEsUUFDakMsU0FBUztBQUFBLFVBQ1A7QUFBQSxVQUNBO0FBQUEsVUFDQTtBQUFBLFVBQ0E7QUFBQSxVQUNBO0FBQUEsVUFDQTtBQUFBLFVBQ0E7QUFBQSxVQUNBO0FBQUEsVUFDQTtBQUFBLFVBQ0E7QUFBQSxVQUNBO0FBQUEsUUFDRjtBQUFBLE1BQ0Y7QUFBQSxNQUNBLEtBQUs7QUFBQSxRQUNILFNBQVM7QUFBQSxVQUNQLG1CQUFtQjtBQUFBLFFBQ3JCO0FBQUEsTUFDRjtBQUFBLE1BQ0EsTUFBTTtBQUFBLE1BQ04sYUFBYTtBQUFBLFFBQ1gsU0FBUztBQUFBLFVBQ1AsY0FBYztBQUFBLFFBQ2hCO0FBQUEsTUFDRjtBQUFBLElBQ0Y7QUFBQSxFQUNGLENBQUM7QUFDSDsiLAogICJuYW1lcyI6IFtdCn0K
