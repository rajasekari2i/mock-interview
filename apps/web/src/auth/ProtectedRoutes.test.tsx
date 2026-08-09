import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "./ProtectedRoute";
import type { AuthState, Role } from "./types";

describe("protected routes", () => {
  it.each([
    [{ status: "loading" }, "Loading protected content…"],
    [{ status: "anonymous" }, "Sign in to continue"],
    [
      {
        status: "error",
        error: {
          code: "FORBIDDEN",
          recovery: "GO_TO_ROLE_HOME",
          message: "Unavailable",
          correlationId: "request-1"
        }
      },
      "Unavailable"
    ]
  ] as const)("renders strict non-authenticated state", (state, text) => {
    render(
      <ProtectedRoute auth={state as AuthState} allowedRoles={["ADMIN"]}>
        <p>Protected</p>
      </ProtectedRoute>
    );
    expect(screen.getByText(text)).toBeInTheDocument();
    expect(screen.queryByText("Protected")).not.toBeInTheDocument();
  });

  it("allows only listed roles", () => {
    const state: AuthState = {
      status: "authenticated",
      current: {
        user: {
          id: "1",
          organizationId: "2",
          displayName: "Admin",
          role: "ADMIN"
        },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    };
    render(
      <ProtectedRoute auth={state} allowedRoles={["ADMIN"] satisfies Role[]}>
        <p>Protected</p>
      </ProtectedRoute>
    );
    expect(screen.getByText("Protected")).toBeInTheDocument();
    const denied = render(
      <ProtectedRoute auth={state} allowedRoles={["MANAGER"] satisfies Role[]}>
        <p>Other protected content</p>
      </ProtectedRoute>
    );
    expect(screen.getByText("This page is not available for your role.")).toBeInTheDocument();
    denied.unmount();
  });
});
