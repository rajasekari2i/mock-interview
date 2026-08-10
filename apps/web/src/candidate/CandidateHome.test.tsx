import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CandidateHome } from "./CandidateHome";

const page = {
  items: [
    {
      id: "interview-1",
      jobDescription: { id: "jd-1", title: "Platform Engineer" },
      scheduledAt: "2026-08-11T09:30:00Z",
      status: "SCHEDULED"
    }
  ],
  page: 1,
  pageSize: 25,
  totalItems: 1,
  totalPages: 1
};

describe("CandidateHome", () => {
  beforeEach(() => vi.stubGlobal("fetch", vi.fn<typeof fetch>()));

  it("renders loading then the self-scoped minimum interview projection", async () => {
    vi.mocked(fetch).mockResolvedValue(Response.json(page));
    render(<CandidateHome />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading interviews");
    expect(screen.queryByText("Candidate")).not.toBeInTheDocument();
    expect(await screen.findByText("Platform Engineer")).toBeVisible();
    expect(screen.getByText("SCHEDULED")).toBeVisible();
    expect(screen.getByText("11 Aug 2026")).toBeVisible();
    expect(screen.getByText(/09:30/)).toBeVisible();
    expect(screen.getByRole("list", { name: "Allocated interviews" })).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("distinguishes empty state and retries a safe error", async () => {
    const user = userEvent.setup();
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response(null, { status: 500 }))
      .mockResolvedValueOnce(Response.json({ ...page, items: [], totalItems: 0, totalPages: 0 }));
    render(<CandidateHome />);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not load");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("No interviews have been allocated yet.")).toBeVisible();
  });
});
