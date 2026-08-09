import { AccessErrorPage, LoginPage } from "./auth/LoginPage";
import { RoleLanding } from "./auth/RoleLanding";
import { useAuth } from "./auth/AuthProvider";
import { SessionExpiredPage } from "./auth/SessionExpiredPage";

export function App(): React.JSX.Element {
  const auth = useAuth();
  if (auth.status === "loading") return <p role="status">Loading your account…</p>;
  if (auth.status === "anonymous") return <LoginPage />;
  if (auth.status === "error" && auth.error.code === "SESSION_EXPIRED") {
    return <SessionExpiredPage reason="expired" />;
  }
  if (auth.status === "error" && auth.error.code === "SESSION_REVOKED") {
    return <SessionExpiredPage reason="revoked" />;
  }
  if (auth.status === "error") return <AccessErrorPage message={auth.error.message} />;
  return <RoleLanding user={auth.current.user} />;
}
