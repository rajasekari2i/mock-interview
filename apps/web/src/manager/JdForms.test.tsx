import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { JdForms } from "./JdForms";

const created = {
  id: "jd-1", title: "Platform Engineer", sourceType: "MANUAL" as const,
  sourceFormat: null, createdAt: "2026-08-10T09:00:00Z"
};

function deferredResponse(): { promise: Promise<Response>; resolve: (response: Response) => void } {
  let resolve!: (response: Response) => void;
  return { promise: new Promise((done) => { resolve = done; }), resolve };
}

describe("JdForms", () => {
  it("uses one form for a manual JD and prevents duplicate submission", async () => {
    const user = userEvent.setup();
    const deferred = deferredResponse();
    const onCreated = vi.fn();
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockReturnValue(deferred.promise));
    render(<JdForms onCreated={onCreated} />);
    expect(screen.getAllByRole("form")).toHaveLength(1);
    await user.type(screen.getByLabelText("JD title"), "Platform Engineer");
    await user.type(screen.getByLabelText("Job description content"), "Build systems");
    const form = screen.getByRole("form");
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(fetch).toHaveBeenCalledTimes(1);
    deferred.resolve(Response.json(created));
    expect(await screen.findByRole("status")).toHaveTextContent("created");
    expect(onCreated).toHaveBeenCalledWith(created);
    expect(screen.getByLabelText("JD title")).toHaveValue("");
  });

  it("switches the same form to upload mode and submits an accepted document", async () => {
    const user = userEvent.setup({ applyAccept: false });
    const uploaded = { ...created, sourceType: "UPLOAD" as const, sourceFormat: "TXT" as const };
    const onCreated = vi.fn();
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(Response.json(uploaded)));
    render(<JdForms onCreated={onCreated} />);
    await user.click(screen.getByRole("button", { name: "Upload document" }));
    expect(screen.getAllByRole("form")).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "Manual text" }));
    expect(screen.getByLabelText("Job description content")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Upload document" }));
    await user.type(screen.getByLabelText("JD title"), "Platform Engineer");
    await user.upload(screen.getByLabelText("JD document"), new File(["content"], "role.txt", { type: "text/plain" }));
    await user.click(screen.getByRole("button", { name: "Upload job description" }));
    expect(await screen.findByRole("status")).toHaveTextContent("created");
    expect(onCreated).toHaveBeenCalledWith(uploaded);
  });

  it("rejects a missing or invalid document without sending it", async () => {
    const user = userEvent.setup({ applyAccept: false });
    vi.stubGlobal("fetch", vi.fn<typeof fetch>());
    render(<JdForms onCreated={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Upload document" }));
    fireEvent.submit(screen.getByRole("form"));
    expect(await screen.findByRole("alert")).toBeVisible();
    await user.upload(screen.getByLabelText("JD document"), new File(["x"], "role.exe"));
    fireEvent.submit(screen.getByRole("form"));
    expect(fetch).not.toHaveBeenCalled();
  });

  it("shows a safe error when creation fails", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 500 })));
    render(<JdForms onCreated={vi.fn()} />);
    await user.type(screen.getByLabelText("JD title"), "Platform Engineer");
    await user.type(screen.getByLabelText("Job description content"), "Build systems");
    await user.click(screen.getByRole("button", { name: "Create job description" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("try again");
  });
});
