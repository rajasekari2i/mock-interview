import { afterEach, describe, expect, it, vi } from "vitest";

const rootMock = vi.hoisted(() => ({ render: vi.fn() }));
vi.mock("react-dom/client", () => ({ createRoot: () => rootMock }));

describe("browser entry point", () => {
  afterEach(() => {
    document.body.replaceChildren();
    vi.resetModules();
    rootMock.render.mockClear();
  });

  it("mounts the application into the required root", async () => {
    const root = document.createElement("div");
    root.id = "root";
    document.body.append(root);
    await import("./main");
    expect(rootMock.render).toHaveBeenCalledOnce();
  });

  it("fails clearly when the application root is absent", async () => {
    await expect(import("./main")).rejects.toThrow("Application root is missing");
  });
});
