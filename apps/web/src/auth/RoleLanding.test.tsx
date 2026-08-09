import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RoleLanding } from "./RoleLanding";
import type { CurrentUser } from "./types";

const shared = {
  id: "10000000-0000-0000-0000-000000000001",
  organizationId: "20000000-0000-0000-0000-000000000001",
  displayName: "Person"
};

describe("role landing", () => {
  it.each([
    [
      { ...shared, role: "CANDIDATE", candidateProfileId: "profile-1" },
      "Your allocated interviews",
      "No interviews have been allocated yet."
    ],
    [{ ...shared, role: "MANAGER" }, "Manager workspace", "Upload job descriptions"],
    [{ ...shared, role: "ADMIN" }, "Application administration", "Manage users"]
  ] as const)("renders the exhaustive role home", (user, heading, content) => {
    render(<RoleLanding user={user as CurrentUser} />);
    expect(screen.getByRole("heading", { name: heading })).toHaveFocus();
    expect(screen.getByText(content)).toBeInTheDocument();
  });
});
