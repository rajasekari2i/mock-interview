import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AccessErrorPage, LoginPage } from "./LoginPage";

describe("Google-only authentication", () => {
  it("offers Google sign-in with no password, reset, registration, or recovery controls", () => {
    const { rerender } = render(<LoginPage />);
    expect(screen.getByRole("main")).toHaveClass("min-h-screen");
    expect(screen.getByRole("heading", { name: "Sign in to MockInterview" }).closest("section")).toHaveClass(
      "rounded-3xl"
    );
    expect(screen.getByRole("link", { name: /continue with google/i })).toHaveClass("bg-white");
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(document.querySelector('input[type="password"]')).toBeNull();
    expect(screen.queryByText(/reset|register|sign up|forgot password/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    expect(screen.queryByText(/choose (an )?organization|choose (a )?role/i)).not.toBeInTheDocument();

    rerender(<AccessErrorPage message="Access is unavailable." />);
    expect(screen.getByRole("main")).toHaveClass("min-h-screen");
    expect(screen.getByRole("alert").closest("section")).toHaveClass("rounded-3xl");
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(document.querySelector('input[type="password"]')).toBeNull();
  });
});
