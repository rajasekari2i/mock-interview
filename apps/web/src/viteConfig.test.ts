// @vitest-environment node

import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";

import config from "../vite.config";

describe("Vite development routing", () => {
  it("proxies API requests to the local backend", () => {
    expect(config).toHaveProperty(
      "server.proxy./api/v1.target",
      "http://localhost:8000"
    );
  });

  it("uses the isolated API target for optimized preview runs", async () => {
    vi.stubEnv("VITE_API_PROXY_TARGET", "http://127.0.0.1:8180");
    vi.resetModules();
    const isolated = (await import("../vite.config")).default;
    expect(isolated).toHaveProperty(
      "preview.proxy./api/v1.target",
      "http://127.0.0.1:8180"
    );
  });

  it("builds the application stylesheet through Tailwind CSS", () => {
    const stylesheet = readFileSync(new URL("./styles.css", import.meta.url), "utf8");
    expect(stylesheet).toContain('@import "tailwindcss";');
  });
});

afterEach(() => {
  vi.unstubAllEnvs();
});
