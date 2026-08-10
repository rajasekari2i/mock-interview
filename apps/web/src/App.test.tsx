import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AuthController } from "./auth/AuthProvider";
import { App } from "./App";

const authMock = vi.hoisted(() => ({ value: {} as AuthController }));
vi.mock("./auth/AuthProvider", () => ({ useAuth: () => authMock.value }));

const logout = (): Promise<void> => Promise.resolve();

function renderApp(path = "/"): void {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );
}

describe("application auth-state routing", () => {
  beforeEach(() => {
    authMock.value = { status: "loading", logout };
  });

  it.each([
    [{ status: "loading", logout }, "Loading your account…"],
    [{ status: "anonymous", logout }, "Sign in to MockInterview"],
    [
      {
        status: "error",
        logout,
        error: {
          code: "SESSION_EXPIRED",
          recovery: "SIGN_IN_AGAIN",
          message: "Expired",
          correlationId: "1"
        }
      },
      "Your session ended"
    ],
    [
      {
        status: "error",
        logout,
        error: {
          code: "SESSION_REVOKED",
          recovery: "SIGN_IN_AGAIN",
          message: "Revoked",
          correlationId: "2"
        }
      },
      "Your session ended"
    ],
    [
      {
        status: "error",
        logout,
        error: {
          code: "FORBIDDEN",
          recovery: "GO_TO_ROLE_HOME",
          message: "Unavailable",
          correlationId: "3"
        }
      },
      "Access unavailable"
    ]
  ] as const)("renders each non-authenticated state", (state, heading) => {
    authMock.value = state as AuthController;
    renderApp();
    expect(screen.getByText(heading)).toBeInTheDocument();
  });

  it("renders the authenticated role landing", () => {
    authMock.value = {
      status: "authenticated",
      logout,
      current: {
        user: { id: "1", organizationId: "2", displayName: "Admin", email: "admin@example.test", profilePictureUrl: null, role: "ADMIN" },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    };
    renderApp();
    expect(screen.getByRole("heading", { name: "Application administration" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Job descriptions" })).toHaveAttribute("href", "/manager/jds");
    expect(screen.queryByRole("heading", { name: "Job descriptions" })).not.toBeInTheDocument();
  });

  it("lets Admin reuse the shared Manager job-description screen", () => {
    authMock.value = {
      status: "authenticated",
      logout,
      current: {
        user: { id: "1", organizationId: "2", displayName: "Admin", email: "admin@example.test", profilePictureUrl: null, role: "ADMIN" },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    };
    renderApp("/manager/jds");
    expect(screen.getByRole("heading", { name: "Job descriptions" })).toHaveFocus();
    expect(screen.getByRole("link", { name: "Create job description" })).toBeInTheDocument();
  });

  it("lets Admin open the shared create job-description route", () => {
    authMock.value = {
      status: "authenticated",
      logout,
      current: {
        user: { id: "1", organizationId: "2", displayName: "Admin", email: "admin@example.test", profilePictureUrl: null, role: "ADMIN" },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    };
    renderApp("/manager/jds/new");
    expect(screen.getByRole("heading", { name: "Create job description" })).toHaveFocus();
  });

  it("resolves the root and deep role home for the current role", () => {
    authMock.value = {
      status: "authenticated",
      logout,
      current: {
        user: { id: "1", organizationId: "2", displayName: "Manager", email: "manager@example.test", profilePictureUrl: null, role: "MANAGER" },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    };
    renderApp("/manager");
    expect(screen.getByRole("heading", { name: "Job descriptions" })).toHaveFocus();
    expect(screen.getByRole("link", { name: "Create job description" })).toHaveAttribute(
      "href",
      "/manager/jds/new"
    );
  });

  it("gives Managers separate JD creation and interview scheduling pages", () => {
    authMock.value = {
      status: "authenticated",
      logout,
      current: {
        user: { id: "1", organizationId: "2", displayName: "Manager", email: "manager@example.test", profilePictureUrl: null, role: "MANAGER" },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    };
    const view = render(
      <MemoryRouter initialEntries={["/manager/jds/new"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByRole("heading", { name: "Create job description" })).toHaveFocus();
    view.unmount();
    renderApp("/manager/interviews/schedule");
    expect(screen.getByRole("heading", { name: "Schedule interview" })).toHaveFocus();
  });

  it("denies a saved cross-role route without rendering protected content", () => {
    authMock.value = {
      status: "authenticated",
      logout,
      current: {
        user: { id: "1", organizationId: "2", displayName: "Manager", email: "manager@example.test", profilePictureUrl: null, role: "MANAGER" },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    };
    renderApp("/admin");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "This page is not available for your role."
    );
    expect(screen.queryByText("Manage users and review application reports.")).not.toBeInTheDocument();
  });

  it("shows a role-safe recovery for an unknown authenticated route", () => {
    authMock.value = {
      status: "authenticated",
      logout,
      current: {
        user: { id: "1", organizationId: "2", displayName: "Admin", email: "admin@example.test", profilePictureUrl: null, role: "ADMIN" },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    };
    renderApp("/saved-page-that-does-not-exist");
    expect(screen.getByRole("heading", { name: "Page unavailable" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Return to your home" })).toHaveAttribute(
      "href",
      "/admin"
    );
  });
});
