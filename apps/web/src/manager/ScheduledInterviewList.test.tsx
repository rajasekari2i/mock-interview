import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScheduledInterviewList } from "./ScheduledInterviewList";

describe("ScheduledInterviewList", () => {
  it("renders empty and minimum Manager history states", () => {
    const view = render(<ScheduledInterviewList items={[]} />);
    expect(screen.getByText("You have not scheduled any interviews yet.")).toBeVisible();
    view.rerender(<ScheduledInterviewList items={[{
      id: "interview-1",
      candidate: { id: "candidate-1", displayName: "Ada", email: "ada@example.test" },
      jobDescription: { id: "jd-1", title: "Engineer" },
      scheduledAt: "2026-08-11T09:00:00Z",
      status: "SCHEDULED"
    }]} />);
    expect(screen.getByText("Ada")).toBeVisible();
    expect(screen.getByText("Engineer")).toBeVisible();
    expect(screen.getByText("SCHEDULED")).toBeVisible();
  });
});
