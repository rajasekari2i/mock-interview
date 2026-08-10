import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { JdList } from "./JdList";

describe("JdList", () => {
  it("shows an owned JD projection or the explicit empty state", () => {
    const view = render(<JdList items={[]} />);
    expect(screen.getByText("You have not created any job descriptions yet.")).toBeVisible();
    view.rerender(
      <JdList
        items={[
          {
            id: "jd-1",
            title: "Platform Engineer",
            sourceType: "UPLOAD",
            sourceFormat: "DOCX",
            createdAt: "2026-08-10T09:00:00Z"
          }
        ]}
      />
    );
    expect(screen.getByText("Platform Engineer")).toBeVisible();
    expect(screen.getByText("DOCX upload")).toBeVisible();
    view.rerender(
      <JdList
        items={[
          {
            id: "jd-2",
            title: "Manual role",
            sourceType: "MANUAL",
            sourceFormat: null,
            createdAt: "2026-08-10T09:00:00Z"
          }
        ]}
      />
    );
    expect(screen.getByText("Manual")).toBeVisible();
  });
});
