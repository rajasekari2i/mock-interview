import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "./AuthProvider";
import { SessionExpiredPage } from "./SessionExpiredPage";

const manager = {
  user: {
    id: "manager-1",
    organizationId: "org-1",
    displayName: "Manager",
    role: "MANAGER"
  },
  session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
};

function LifecycleProbe(): React.JSX.Element {
  const auth = useAuth();
  return (
    <div>
      <span>{auth.status}</span>
      <button type="button" onClick={() => void auth.logout()}>
        Sign out
      </button>
    </div>
  );
}

describe("session lifecycle", () => {
  it("globally logs out, clears protected state, and broadcasts auth loss", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(Response.json(manager))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    render(
      <AuthProvider>
        <LifecycleProbe />
      </AuthProvider>
    );
    await screen.findByText("authenticated");
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    await screen.findByText("anonymous");
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/auth/logout",
      expect.objectContaining({ method: "POST" })
    );
    expect(localStorage.getItem("mi_auth_event")).toContain("logged-out");
  });

  it("clears authenticated state when another tab reports authentication loss", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(Response.json(manager)));
    render(
      <AuthProvider>
        <LifecycleProbe />
      </AuthProvider>
    );
    await screen.findByText("authenticated");
    window.dispatchEvent(
      new StorageEvent("storage", { key: "mi_auth_event", newValue: "logged-out:other" })
    );
    await waitFor(() => expect(screen.getByText("anonymous")).toBeInTheDocument());
  });

  it("moves focus to the expired-session heading and offers sign-in recovery", () => {
    render(<SessionExpiredPage reason="expired" />);
    expect(screen.getByRole("heading", { name: "Your session ended" })).toHaveFocus();
    expect(screen.getByRole("link", { name: "Sign in again" })).toHaveAttribute(
      "href",
      "/api/v1/auth/google/login"
    );
    render(<SessionExpiredPage reason="revoked" />);
    expect(screen.getByText("Your access changed and this session was closed.")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Sign in again" }).at(-1)).toHaveAttribute(
      "href",
      "/api/v1/auth/google/login"
    );
  });
});
