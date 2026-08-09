import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AuthController } from "./auth/AuthProvider";
import { App } from "./App";

const authMock = vi.hoisted(() => ({ value: {} as AuthController }));
vi.mock("./auth/AuthProvider", () => ({ useAuth: () => authMock.value }));

const logout = (): Promise<void> => Promise.resolve();

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
    render(<App />);
    expect(screen.getByText(heading)).toBeInTheDocument();
  });

  it("renders the authenticated role landing", () => {
    authMock.value = {
      status: "authenticated",
      logout,
      current: {
        user: { id: "1", organizationId: "2", displayName: "Admin", role: "ADMIN" },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    };
    render(<App />);
    expect(screen.getByRole("heading", { name: "Application administration" })).toBeInTheDocument();
  });
});
