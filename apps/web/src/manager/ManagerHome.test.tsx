import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import {
  ManagerCreateJdPage,
  ManagerHome,
  ManagerSchedulePage
} from "./ManagerHome";

const emptyPage = { items: [], page: 1, pageSize: 25, totalItems: 0, totalPages: 0 };

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  return input instanceof URL ? input.href : input.url;
}

describe("Manager pages", () => {
  it("shows owned job descriptions and a top-right create action", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(Response.json(emptyPage)));
    render(<MemoryRouter><ManagerHome /></MemoryRouter>);
    expect(await screen.findByText("You have not created any job descriptions yet.")).toBeVisible();
    expect(screen.queryByText("Manager")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create job description" })).toHaveAttribute("href", "/manager/jds/new");
  });

  it("reuses the list for Admin and exposes the shared creation flow", async () => {
    const jd = { id: "jd-admin", organizationId: "org-1", title: "Shared role", sourceType: "MANUAL", sourceFormat: null, createdAt: "2026-08-10T09:00:00Z", createdBy: { id: "manager-1", displayName: "Manager" } };
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(Response.json({ ...emptyPage, items: [jd] })));
    render(<MemoryRouter><ManagerHome access="admin" /></MemoryRouter>);
    expect(await screen.findByText("Shared role")).toBeVisible();
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/admin/job-descriptions"), expect.anything());
    expect(screen.queryByText("Administration")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create job description" })).toHaveAttribute("href", "/manager/jds/new");
  });

  it("retries a failed job-description list", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(null, { status: 500 }))
      .mockResolvedValueOnce(Response.json(emptyPage)));
    render(<MemoryRouter><ManagerHome /></MemoryRouter>);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not load");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("You have not created any job descriptions yet.")).toBeVisible();
  });

  it("hosts manual and upload creation in one page and returns to the list", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(Response.json({
      id: "jd-1", title: "Engineer", sourceType: "MANUAL", sourceFormat: null,
      createdAt: "2026-08-10T09:00:00Z"
    })));
    render(<MemoryRouter><ManagerCreateJdPage /></MemoryRouter>);
    expect(screen.queryByText("Job descriptions")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to job descriptions" })).toHaveAttribute("href", "/manager/jds");
    await user.type(screen.getByLabelText("JD title"), "Engineer");
    await user.type(screen.getByLabelText("Job description content"), "Build reliable systems");
    await user.click(screen.getByRole("button", { name: "Create job description" }));
    expect(await screen.findByRole("status")).toHaveTextContent("created");
  });

  it("loads scheduling choices and interview history on its own page", async () => {
    const user = userEvent.setup();
    const jd = { id: "jd-1", title: "Engineer", sourceType: "MANUAL", sourceFormat: null, createdAt: "2026-08-10T09:00:00Z" };
    const candidate = { id: "candidate-1", displayName: "Ada", email: "ada@example.test" };
    const interview = { id: "interview-1", candidate, jobDescription: { id: jd.id, title: jd.title }, scheduledAt: "2099-01-01T09:00:00.000Z", status: "SCHEDULED" };
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "00000000-0000-0000-0000-000000000004") });
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockImplementation((input, init) => {
      const url = requestUrl(input);
      if (url.includes("job-descriptions")) return Promise.resolve(Response.json({ ...emptyPage, items: [jd] }));
      if (url.includes("candidates")) return Promise.resolve(Response.json({ ...emptyPage, items: [candidate] }));
      if (init?.method === "POST") return Promise.resolve(Response.json(interview, { status: 201 }));
      return Promise.resolve(Response.json(emptyPage));
    }));
    render(<ManagerSchedulePage />);
    expect(screen.queryByText("Manager")).not.toBeInTheDocument();
    expect(await screen.findByLabelText("Candidate")).toBeEnabled();
    expect(screen.getByText("You have not scheduled any interviews yet.")).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Candidate"), candidate.id);
    await user.selectOptions(screen.getByLabelText("Job description"), jd.id);
    await user.type(screen.getByLabelText("Interview date"), "2099-01-01");
    await user.type(screen.getByLabelText("Interview time"), "09:00");
    await user.click(screen.getByRole("button", { name: "Schedule interview" }));
    expect(await screen.findByText("Ada")).toBeVisible();
  });

  it("degrades unavailable schedule choices safely", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockRejectedValue(new Error("unavailable")));
    render(<ManagerSchedulePage />);
    expect(await screen.findByText("An active candidate and one of your JDs are required.")).toBeVisible();
    expect(screen.getByText("You have not scheduled any interviews yet.")).toBeVisible();
  });
});
