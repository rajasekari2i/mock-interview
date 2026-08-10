import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { currentUser } from "../test/factories";
import { ProfilePage } from "./ProfilePage";

describe("ProfilePage", () => {
  it("shows only the authenticated user's verified identity", () => {
    const user = {
      ...currentUser("CANDIDATE"),
      displayName: "Ada Lovelace",
      email: "ada@example.test",
      profilePictureUrl: "https://images.example.test/ada.png"
    };
    render(<ProfilePage user={user} />);
    expect(screen.getByRole("heading", { name: "Your profile" })).toHaveFocus();
    expect(screen.getByText("Ada Lovelace")).toBeVisible();
    expect(screen.getByText("ada@example.test")).toBeVisible();
    expect(screen.getByRole("img", { name: "Ada Lovelace profile picture" })).toBeVisible();
  });
});
