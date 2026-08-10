import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders a human-readable status without relying on color", () => {
    render(<StatusBadge status="IN_PROGRESS" />);
    expect(screen.getByText("In progress")).toHaveClass("rounded-full", "bg-emerald-50");
  });

  it("accepts an explicit label", () => {
    render(<StatusBadge status="SCHEDULED" label="Scheduled interview" />);
    expect(screen.getByText("Scheduled interview")).toHaveClass("font-bold", "text-emerald-700");
  });
});
