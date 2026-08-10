import { defineConfig } from "@playwright/test";

const baseURL = process.env.PERFORMANCE_FRONTEND_ORIGIN;
if (baseURL === undefined) {
  throw new Error("PERFORMANCE_FRONTEND_ORIGIN is required");
}

export default defineConfig({
  testDir: "./performance",
  outputDir: "./test-results/performance",
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  use: {
    baseURL,
    browserName: "chromium",
    trace: "off",
    screenshot: "off",
    video: "off"
  }
});
