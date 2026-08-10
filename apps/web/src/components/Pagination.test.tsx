import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Pagination } from "./Pagination";

describe("Pagination", () => {
  it("announces page state and enforces boundaries", async () => {
    const user = userEvent.setup();
    const onPage = vi.fn();
    const view = render(<Pagination label="User pagination" page={1} totalPages={3} totalItems={51} onPage={onPage} />);
    expect(screen.getByRole("navigation", { name: "User pagination" })).toBeVisible();
    expect(screen.getByText("Page 1 of 3 · 51 total")).toBeVisible();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(onPage).toHaveBeenCalledWith(2);
    view.rerender(<Pagination label="User pagination" page={3} totalPages={3} totalItems={51} onPage={onPage} />);
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(onPage).toHaveBeenCalledWith(2);
  });
});
