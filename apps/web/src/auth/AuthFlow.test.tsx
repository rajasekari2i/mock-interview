import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { authFetch, logoutEverywhere, readCsrfCookie } from "./api";
import { AuthProvider, useAuth } from "./AuthProvider";
import {
  decodeCallbackError,
  decodeCurrentUserResponse,
  decodeErrorEnvelope
} from "./decoders";

const candidateResponse = {
  user: {
    id: "10000000-0000-0000-0000-000000000001",
    organizationId: "20000000-0000-0000-0000-000000000001",
    displayName: "Candidate",
    role: "CANDIDATE",
    candidateProfileId: "30000000-0000-0000-0000-000000000001"
  },
  session: {
    absoluteExpiresAt: "2026-08-09T18:00:00Z",
    idleExpiresAt: "2026-08-09T12:00:00Z"
  }
};

function Probe(): React.JSX.Element {
  const auth = useAuth();
  return <div>{auth.status}</div>;
}

describe("authentication runtime boundaries", () => {
  it("decodes role-discriminated current-user and rejects malformed candidate context", () => {
    expect(decodeCurrentUserResponse(candidateResponse).user.role).toBe("CANDIDATE");
    expect(() =>
      decodeCurrentUserResponse({
        ...candidateResponse,
        user: { ...candidateResponse.user, candidateProfileId: undefined }
      })
    ).toThrow();
  });

  it("decodes only approved recovery errors", () => {
    expect(
      decodeErrorEnvelope({
        error: {
          code: "OAUTH_PROVIDER_UNAVAILABLE",
          recovery: "RETRY",
          message: "Try again.",
          correlationId: "request-1"
        }
      }).error.recovery
    ).toBe("RETRY");
    expect(() =>
      decodeErrorEnvelope({ error: { code: "RAW_PROVIDER_ERROR", recovery: "PANIC" } })
    ).toThrow();
  });

  it("parses only allowlisted callback errors with local safe recovery copy", () => {
    expect(
      decodeCallbackError(
        "?code=ACCESS_NOT_PROVISIONED&correlation_id=opaque-request"
      )
    ).toEqual({
      code: "ACCESS_NOT_PROVISIONED",
      recovery: "CONTACT_ADMIN",
      message: "Access is unavailable. Contact your administrator.",
      correlationId: "opaque-request"
    });
    expect(decodeCallbackError("?code=RAW_PROVIDER_ERROR&correlation_id=id")).toBeNull();
    expect(decodeCallbackError("?code=OAUTH_CANCELLED")).toBeNull();
  });

  it("surfaces a callback error without making a bootstrap request", async () => {
    window.history.replaceState(
      {},
      "",
      "/auth/error?code=OAUTH_PROVIDER_UNAVAILABLE&correlation_id=request-4"
    );
    const fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetchMock);
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    expect(await screen.findByText("error")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    window.history.replaceState({}, "", "/");
  });

  it("copies the readable CSRF cookie to mutations and always includes credentials", async () => {
    Object.defineProperty(document, "cookie", {
      configurable: true,
      value: "other=value; mi_csrf=csrf%20token"
    });
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await authFetch("/auth/logout", { method: "POST" });

    expect(readCsrfCookie()).toBe("csrf token");
    const [url, request] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/auth/logout");
    expect(request?.credentials).toBe("include");
    expect(new Headers(request?.headers).get("X-CSRF-Token")).toBe("csrf token");

    Object.defineProperty(document, "cookie", { configurable: true, value: "other=value" });
    await authFetch("/auth/me");
    expect(readCsrfCookie()).toBeNull();
  });

  it("bootstraps loading to authenticated and clears to anonymous on 401", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(Response.json(candidateResponse))
      .mockResolvedValueOnce(
        Response.json(
          {
            error: {
              code: "AUTHENTICATION_REQUIRED",
              recovery: "SIGN_IN_AGAIN",
              message: "Sign in.",
              correlationId: "request-2"
            }
          },
          { status: 401 }
        )
      );
    vi.stubGlobal("fetch", fetchMock);
    const first = render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await screen.findByText("authenticated");
    first.unmount();

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByText("anonymous")).toBeInTheDocument());
  });

  it("renders approved API and generic bootstrap errors and rejects failed logout", async () => {
    const apiFailure = {
      error: {
        code: "OAUTH_PROVIDER_UNAVAILABLE",
        recovery: "RETRY",
        message: "Try again.",
        correlationId: "request-3"
      }
    };
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(Response.json(apiFailure, { status: 503 }))
    );
    const first = render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await screen.findByText("error");
    first.unmount();

    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockRejectedValue(new Error("offline")));
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await screen.findByText("error");

    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(Response.json(apiFailure, { status: 403 }))
    );
    await expect(logoutEverywhere()).rejects.toMatchObject({ status: 403 });
  });

  it("requires useAuth to be nested inside the provider", () => {
    expect(() => render(<Probe />)).toThrow("useAuth must be used inside AuthProvider");
  });

  it("rejects non-object and incomplete runtime responses", () => {
    expect(() => decodeCurrentUserResponse(null)).toThrow("Expected an object response");
    expect(() => decodeCurrentUserResponse([])).toThrow("Expected an object response");
    for (const role of ["MANAGER", "ADMIN"] as const) {
      expect(
        decodeCurrentUserResponse({
          ...candidateResponse,
          user: { ...candidateResponse.user, role, candidateProfileId: undefined }
        }).user.role
      ).toBe(role);
    }
    expect(() =>
      decodeCurrentUserResponse({
        ...candidateResponse,
        user: { ...candidateResponse.user, role: "UNKNOWN" }
      })
    ).toThrow("Unknown role");
    expect(() => decodeErrorEnvelope({ error: { code: 1 } })).toThrow("Expected code");
    expect(() =>
      decodeErrorEnvelope({
        error: {
          code: "AUTHENTICATION_REQUIRED",
          recovery: "UNKNOWN",
          message: "Message",
          correlationId: "id"
        }
      })
    ).toThrow("Unknown authentication error contract");
    expect(() =>
      decodeErrorEnvelope({
        error: {
          code: "AUTHENTICATION_REQUIRED",
          recovery: "SIGN_IN_AGAIN",
          message: "",
          correlationId: "id"
        }
      })
    ).toThrow("Expected message");
  });

  it("ignores a bootstrap completion after the provider unmounts", async () => {
    let rejectRequest: ((reason: unknown) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockImplementation(
        () =>
          new Promise<Response>((_resolve, reject) => {
            rejectRequest = reject;
          })
      )
    );
    const view = render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    view.unmount();
    rejectRequest?.(new Error("late failure"));
    await Promise.resolve();
  });
});
