import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AdminHome } from "./AdminHome";

const user = { id: "user-1", organizationId: "org-1", displayName: "Ada", email: "ada@example.test", role: "MANAGER", status: "ACTIVE" };
const otherUser = { ...user, id: "user-2", displayName: "Bob", email: "bob@example.test" };
const page = (items: unknown[], current = 1) => ({ items, page: current, pageSize: 25, totalItems: 26, totalPages: 2 });

describe("AdminHome", () => {
  it("loads users without rendering job descriptions and opens a fetched user detail", async () => {
    const actor = userEvent.setup();
    window.history.replaceState(null, "", "/admin?usersPage=2");
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockImplementation((input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      if (url.endsWith("/users/user-1/role")) return Promise.resolve(Response.json({ ...user, role: "ADMIN", profilePictureUrl: null, candidateProfileId: null }));
      if (url.endsWith("/users/user-1")) return Promise.resolve(Response.json({ ...user, profilePictureUrl: null, candidateProfileId: null }));
      if (url.includes("/admin/users")) return Promise.resolve(Response.json(page([user, otherUser], 2)));
      return Promise.reject(new Error("unexpected request"));
    }));
    render(<AdminHome />);
    expect(await screen.findByText("Ada")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Job descriptions" })).not.toBeInTheDocument();
    expect(screen.getByText("Page 2 of 2 · 26 total")).toBeVisible();
    await actor.click(screen.getByRole("button", { name: "View details for Ada" }));
    expect(await screen.findByRole("dialog")).toBeVisible();
    await actor.selectOptions(screen.getByLabelText("Role"), "ADMIN");
    await actor.click(screen.getByRole("button", { name: "Save role" }));
    expect(await screen.findByRole("status")).toHaveTextContent("updated");
    await actor.click(screen.getByRole("button", { name: "Close" }));
    const previous = screen.getAllByRole("button", { name: "Previous" }).find(
      (button) => !(button as HTMLButtonElement).disabled
    );
    expect(previous).toBeDefined();
    await actor.click(previous as HTMLButtonElement);
    expect(window.location.search).toContain("usersPage=1");
  });

  it("shows a retryable user-list failure", async () => {
    const actor = userEvent.setup();
    window.history.replaceState(null, "", "/admin");
    let failures = 1;
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockImplementation(() => {
      if (failures > 0) { failures -= 1; return Promise.resolve(new Response(null, { status: 500 })); }
      return Promise.resolve(Response.json(page([])));
    }));
    render(<AdminHome />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Users could not load");
    await actor.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("No users found.")).toBeVisible();
  });

  it("reports a detail failure and normalizes invalid URL pages", async () => {
    const actor = userEvent.setup();
    window.history.replaceState(null, "", "/admin?usersPage=bad");
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockImplementation((input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      if (url.endsWith("/users/user-1")) return Promise.resolve(new Response(null, { status: 500 }));
      if (url.includes("/admin/users")) return Promise.resolve(Response.json(page([user])));
      return Promise.reject(new Error("unexpected request"));
    }));
    render(<AdminHome />);
    await actor.click(await screen.findByRole("button", { name: "View details for Ada" }));
    expect(await screen.findByText("User details could not load.")).toBeVisible();
  });
});
