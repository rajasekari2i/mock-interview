import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { OrganizationsPage } from "./OrganizationsPage";

const organization = {
  id: "org-1",
  name: "Ideas2IT",
  slug: "ideas2it",
  status: "ACTIVE",
  createdAt: "2026-08-10T09:00:00Z",
  updatedAt: "2026-08-10T09:00:00Z"
};

describe("OrganizationsPage", () => {
  it("lists organizations and creates an active organization", async () => {
    const actor = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn<typeof fetch>()
      .mockResolvedValueOnce(Response.json({ items: [organization] }))
      .mockResolvedValueOnce(Response.json({ ...organization, id: "org-2", name: "Acme", slug: "acme" }, { status: 201 })));
    render(<OrganizationsPage />);

    expect(await screen.findByRole("cell", { name: "Ideas2IT" })).toBeVisible();
    await actor.type(screen.getByLabelText("Organization name"), "Acme");
    await actor.type(screen.getByLabelText("Organization slug"), "acme");
    await actor.click(screen.getByRole("button", { name: "Create organization" }));

    expect(await screen.findByRole("status")).toHaveTextContent("created");
    expect(screen.getByRole("cell", { name: "Acme" })).toBeVisible();
  });

  it("shows safe load and creation errors with retry", async () => {
    const actor = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(null, { status: 500 }))
      .mockResolvedValueOnce(Response.json({ items: [] }))
      .mockResolvedValueOnce(new Response(null, { status: 409 })));
    render(<OrganizationsPage />);

    await actor.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByText("No organizations found.")).toBeVisible();
    await actor.type(screen.getByLabelText("Organization name"), "Acme");
    await actor.type(screen.getByLabelText("Organization slug"), "acme");
    await actor.click(screen.getByRole("button", { name: "Create organization" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be created");
  });
});
