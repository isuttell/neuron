import { defineConfig, mergeConfig } from "vite";
import { defineConfig as defineVitestConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default mergeConfig(
  viteConfig({ mode: "test" }),
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
          "test/**",
        ],
      },
      css: {
        modules: {
          classNameStrategy: "non-scoped",
        },
      },
      pool: "threads",
      poolOptions: {
        threads: {
          singleThread: false,
        },
      },
    },
  })
);
