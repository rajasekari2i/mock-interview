import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { JdsTable } from "./JdsTable";

describe("JdsTable", () => {
  it("renders empty and minimum application-wide JD rows", () => {
    const view = render(<JdsTable items={[]} />);
    expect(screen.getByText("No job descriptions found.")).toBeVisible();
    view.rerender(<JdsTable items={[{
      id: "jd-1", organizationId: "org-1", title: "Engineer", sourceType: "MANUAL",
      sourceFormat: null, createdAt: "2026-08-10T09:00:00Z",
      createdBy: { id: "user-1", displayName: "Ada" }
    }]} />);
    expect(screen.getByText("Engineer")).toBeVisible();
    expect(screen.getByText("Ada")).toBeVisible();
  });
});
