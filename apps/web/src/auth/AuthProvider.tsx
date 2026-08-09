/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { ApiError, fetchCurrentUser, logoutEverywhere } from "./api";
import { decodeCallbackError } from "./decoders";
import type { AuthState } from "./types";

export type AuthController = AuthState & { logout: () => Promise<void> };

const AuthContext = createContext<AuthController | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [state, setState] = useState<AuthState>(() => {
    const callbackError = decodeCallbackError(window.location.search);
    return callbackError === null
      ? { status: "loading" }
      : { status: "error", error: callbackError };
  });

  useEffect(() => {
    const clearFromAnotherTab = (event: StorageEvent): void => {
      if (event.key === "mi_auth_event" && event.newValue?.startsWith("logged-out:")) {
        setState({ status: "anonymous" });
      }
    };
    window.addEventListener("storage", clearFromAnotherTab);
    return () => {
      window.removeEventListener("storage", clearFromAnotherTab);
    };
  }, []);

  useEffect(() => {
    if (decodeCallbackError(window.location.search) !== null) return;
    let active = true;
    void fetchCurrentUser()
      .then((current) => {
        if (active) setState({ status: "authenticated", current });
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (
          error instanceof ApiError &&
          error.envelope.error.code === "AUTHENTICATION_REQUIRED"
        ) {
          setState({ status: "anonymous" });
        } else if (error instanceof ApiError) {
          setState({ status: "error", error: error.envelope.error });
        } else {
          setState({
            status: "error",
            error: {
              code: "OAUTH_PROVIDER_UNAVAILABLE",
              recovery: "RETRY",
              message: "Sign-in is temporarily unavailable. Try again.",
              correlationId: "unavailable"
            }
          });
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<AuthController>(
    () => ({
      ...state,
      logout: async () => {
        await logoutEverywhere();
        setState({ status: "anonymous" });
        localStorage.setItem("mi_auth_event", `logged-out:${String(Date.now())}`);
      }
    }),
    [state]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthController {
  const value = useContext(AuthContext);
  if (value === null) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
