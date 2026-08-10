import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ScheduleInterviewForm } from "./ScheduleInterviewForm";

const candidate = { id: "candidate-1", displayName: "Ada", email: "ada@example.test" };
const jd = {
  id: "jd-1", title: "Engineer", sourceType: "MANUAL" as const, sourceFormat: null,
  createdAt: "2026-08-10T09:00:00Z"
};
const interview = {
  id: "interview-1", candidate, jobDescription: { id: jd.id, title: jd.title },
  scheduledAt: "2099-01-01T09:00:00Z", status: "SCHEDULED" as const
};

describe("ScheduleInterviewForm", () => {
  it("validates required resources and schedules one future interview", async () => {
    const user = userEvent.setup();
    const onScheduled = vi.fn();
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(Response.json(interview, { status: 201 })));
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "00000000-0000-0000-0000-000000000001") });
    render(<ScheduleInterviewForm candidates={[candidate]} jobDescriptions={[jd]} onScheduled={onScheduled} />);
    fireEvent.submit(screen.getByRole("button", { name: "Schedule interview" }).closest("form") as HTMLFormElement);
    expect(await screen.findByRole("alert")).toHaveTextContent("Choose a candidate");
    await user.selectOptions(screen.getByLabelText("Candidate"), candidate.id);
    await user.selectOptions(screen.getByLabelText("Job description"), jd.id);
    await user.type(screen.getByLabelText("Interview date"), "2099-01-01");
    await user.type(screen.getByLabelText("Interview time"), "09:00");
    await user.click(screen.getByRole("button", { name: "Schedule interview" }));
    expect(await screen.findByRole("status")).toHaveTextContent("scheduled");
    expect(onScheduled).toHaveBeenCalledWith(interview);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("retains an intent key for retry and guards duplicate submissions", async () => {
    const user = userEvent.setup();
    let resolve!: (response: Response) => void;
    const pending = new Promise<Response>((done) => { resolve = done; });
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockReturnValueOnce(pending).mockResolvedValueOnce(new Response(null, { status: 409 })));
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "00000000-0000-0000-0000-000000000002") });
    render(<ScheduleInterviewForm candidates={[candidate]} jobDescriptions={[jd]} onScheduled={vi.fn()} />);
    await user.selectOptions(screen.getByLabelText("Candidate"), candidate.id);
    await user.selectOptions(screen.getByLabelText("Job description"), jd.id);
    await user.type(screen.getByLabelText("Interview date"), "2099-01-01");
    await user.type(screen.getByLabelText("Interview time"), "09:00");
    const form = screen.getByRole("button", { name: "Schedule interview" }).closest("form") as HTMLFormElement;
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(fetch).toHaveBeenCalledTimes(1);
    resolve(new Response(null, { status: 500 }));
    expect(await screen.findByRole("alert")).toHaveTextContent("could not");
    await user.click(screen.getByRole("button", { name: "Schedule interview" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("already used");
    const headers = new Headers(vi.mocked(fetch).mock.calls[0]?.[1]?.headers);
    expect(headers.get("Idempotency-Key")).toBe("00000000-0000-0000-0000-000000000002");
  });

  it("reports an empty-resource state", () => {
    render(<ScheduleInterviewForm candidates={[]} jobDescriptions={[]} onScheduled={vi.fn()} />);
    expect(screen.getByText("An active candidate and one of your JDs are required.")).toBeVisible();
  });

  it("rejects past time and handles a non-Error transport failure", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockRejectedValue("offline"));
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "00000000-0000-0000-0000-000000000003") });
    render(<ScheduleInterviewForm candidates={[candidate]} jobDescriptions={[jd]} onScheduled={vi.fn()} />);
    await user.selectOptions(screen.getByLabelText("Candidate"), candidate.id);
    await user.selectOptions(screen.getByLabelText("Job description"), jd.id);
    await user.type(screen.getByLabelText("Interview date"), "2000-01-01");
    await user.type(screen.getByLabelText("Interview time"), "09:00");
    await user.click(screen.getByRole("button", { name: "Schedule interview" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("future");
    await user.clear(screen.getByLabelText("Interview date"));
    await user.type(screen.getByLabelText("Interview date"), "2099-01-01");
    await user.click(screen.getByRole("button", { name: "Schedule interview" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("could not");
  });
});
