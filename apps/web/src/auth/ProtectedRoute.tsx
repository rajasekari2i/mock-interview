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
  if (auth.status === "loading") return <p className="rounded-xl bg-indigo-50 p-4 font-semibold text-indigo-800" role="status">Loading protected content…</p>;
  if (auth.status === "anonymous") return <p className="rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">Sign in to continue</p>;
  if (auth.status === "error") return <p className="rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">{auth.error.message}</p>;
  if (!allowedRoles.includes(auth.current.user.role)) {
    return <p className="rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">This page is not available for your role.</p>;
  }
  return <>{children}</>;
}
