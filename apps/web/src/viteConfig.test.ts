// @vitest-environment node

import { describe, expect, it } from "vitest";

import config from "../vite.config";

describe("Vite development routing", () => {
  it("proxies API requests to the local backend", () => {
    expect(config).toHaveProperty(
      "server.proxy./api/v1.target",
      "http://localhost:8000"
    );
  });
});
