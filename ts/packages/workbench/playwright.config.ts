import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.WORKBENCH_QA_PORT ?? 5174);
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "./tests/workbench-qa",
  outputDir: "../../.playwright/workbench/test-results",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"], ["html", { outputFolder: "../../.playwright/workbench/report", open: "never" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: {
    command: `WORKBENCH_QA=1 bun run dev -- --host 127.0.0.1 --port ${port} --strictPort`,
    cwd: ".",
    url: baseURL,
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
    {
      name: "tablet",
      use: { ...devices["iPad (gen 7)"], browserName: "chromium" },
    },
    {
      name: "mobile",
      use: { ...devices["Pixel 5"] },
    },
  ],
});
