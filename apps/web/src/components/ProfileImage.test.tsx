import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProfileImage } from "./ProfileImage";

describe("ProfileImage", () => {
  it("renders a provider image with useful alternative text", () => {
    render(
      <ProfileImage
        displayName="Ada Lovelace"
        src="https://images.example.test/ada.png"
      />
    );
    expect(screen.getByRole("img", { name: "Ada Lovelace profile picture" })).toHaveAttribute(
      "src",
      "https://images.example.test/ada.png"
    );
    const view = render(
      <ProfileImage
        displayName="Ada Lovelace"
        src="https://images.example.test/decorative.png"
        decorative
      />
    );
    expect(view.container.querySelector('img[alt=""]')).not.toBeNull();
  });

  it("falls back to initials when no URL is available or the image fails", () => {
    const view = render(<ProfileImage displayName="Ada Lovelace" src={null} />);
    expect(screen.getByRole("img", { name: "Ada Lovelace profile placeholder" })).toHaveTextContent(
      "AL"
    );
    view.rerender(
      <ProfileImage displayName="Ada Lovelace" src="https://images.example.test/broken.png" />
    );
    fireEvent.error(screen.getByRole("img", { name: "Ada Lovelace profile picture" }));
    expect(screen.getByRole("img", { name: "Ada Lovelace profile placeholder" })).toBeVisible();
  });

  it("uses a safe person glyph when the name has no initials", () => {
    render(<ProfileImage displayName=" " src={null} decorative />);
    expect(screen.getByText("●")).toHaveAttribute("aria-hidden", "true");
  });
});
