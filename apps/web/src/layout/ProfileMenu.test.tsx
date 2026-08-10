import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { currentUser } from "../test/factories";
import { ProfileMenu } from "./ProfileMenu";

describe("ProfileMenu", () => {
  it("opens accessibly and restores trigger focus after Escape", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ProfileMenu user={currentUser("MANAGER")} onLogout={vi.fn()} />
      </MemoryRouter>
    );
    const trigger = screen.getByRole("button", { name: "Open profile menu" });
    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: "Profile" })).toHaveAttribute("href", "/profile");
    await user.click(screen.getByRole("link", { name: "Profile" }));
    expect(screen.queryByRole("link", { name: "Profile" })).not.toBeInTheDocument();
    await user.click(trigger);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("link", { name: "Profile" })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("closes outside and invokes logout once", async () => {
    const user = userEvent.setup();
    const logout = vi.fn().mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <div>Outside</div>
        <ProfileMenu user={currentUser("ADMIN")} onLogout={logout} />
      </MemoryRouter>
    );
    await user.click(screen.getByRole("button", { name: "Open profile menu" }));
    await user.click(screen.getByText("Outside"));
    expect(screen.queryByRole("button", { name: "Logout" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open profile menu" }));
    await user.click(screen.getByRole("button", { name: "Logout" }));
    expect(logout).toHaveBeenCalledTimes(1);
  });
});
