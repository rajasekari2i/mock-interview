import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { UserDetailsDialog } from "./UserDetailsDialog";

const user = {
  id: "user-1", organizationId: "org-1", displayName: "Ada", email: "ada@example.test",
  role: "CANDIDATE" as const, status: "ACTIVE" as const,
  profilePictureUrl: null, candidateProfileId: "profile-1"
};

describe("UserDetailsDialog", () => {
  it("shows available details, saves a supported role, closes, and restores focus", async () => {
    const actor = userEvent.setup();
    const opener = document.createElement("button");
    document.body.append(opener);
    opener.focus();
    const onClose = vi.fn();
    const onSaved = vi.fn();
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(Response.json({ ...user, role: "MANAGER" })));
    render(<UserDetailsDialog user={user} onClose={onClose} onSaved={onSaved} />);
    expect(screen.getByRole("dialog")).toHaveAttribute("open");
    expect(screen.getByText("ada@example.test")).toBeVisible();
    await actor.selectOptions(screen.getByLabelText("Role"), "MANAGER");
    await actor.click(screen.getByRole("button", { name: "Save role" }));
    expect(await screen.findByRole("status")).toHaveTextContent("updated");
    expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ role: "MANAGER" }));
    await actor.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledOnce();
    expect(opener).toHaveFocus();
    opener.remove();
  });

  it("reports safe save failure and handles Escape cancellation", async () => {
    const actor = userEvent.setup();
    const onClose = vi.fn();
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 403 })));
    render(<UserDetailsDialog user={user} onClose={onClose} onSaved={vi.fn()} />);
    await actor.click(screen.getByRole("button", { name: "Save role" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("could not");
    const dialog = screen.getByRole("dialog");
    dialog.dispatchEvent(new Event("cancel", { cancelable: true }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
