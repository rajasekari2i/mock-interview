import type { AuthState, Role } from "./types";

export function ProtectedRoute({
  auth,
  allowedRoles,
  children
}: {
  auth: AuthState;
  allowedRoles: readonly Role[];
  children: React.ReactNode;
}): React.JSX.Element {
  if (auth.status === "loading") return <p role="status">Loading protected content…</p>;
  if (auth.status === "anonymous") return <p role="alert">Sign in to continue</p>;
  if (auth.status === "error") return <p role="alert">{auth.error.message}</p>;
  if (!allowedRoles.includes(auth.current.user.role)) {
    return <p role="alert">This page is not available for your role.</p>;
  }
  return <>{children}</>;
}
