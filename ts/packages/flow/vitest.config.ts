import { defineConfig } from "vitest/config";
export default defineConfig({
  test: {
    include: ["src/**/*.test.ts", "src/**/*.spec.ts"],
    exclude: ["dist/**", "node_modules/**"],
    globals: true,
  },
});
