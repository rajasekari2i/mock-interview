import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { UsersTable } from "./UsersTable";

describe("UsersTable", () => {
  it("renders empty and semantic user rows with a details control", async () => {
    const user = userEvent.setup();
    const onDetails = vi.fn();
    const view = render(<UsersTable items={[]} onDetails={onDetails} />);
    expect(screen.getByText("No users found.")).toBeVisible();
    const item = { id: "user-1", organizationId: "org-1", displayName: "Ada", email: "ada@example.test", role: "MANAGER" as const, status: "ACTIVE" as const };
    view.rerender(<UsersTable items={[item]} onDetails={onDetails} />);
    await user.click(screen.getByRole("button", { name: "View details for Ada" }));
    expect(onDetails).toHaveBeenCalledWith(item);
  });
});
