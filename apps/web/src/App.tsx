import { Link, Navigate, Route, Routes } from "react-router-dom";

import { AdminHome } from "./admin/AdminHome";
import { OrganizationsPage } from "./admin/OrganizationsPage";
import { AccessErrorPage, LoginPage } from "./auth/LoginPage";
import { useAuth } from "./auth/AuthProvider";
import { FocusedHeading } from "./auth/FocusedHeading";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { SessionExpiredPage } from "./auth/SessionExpiredPage";
import type { AuthController } from "./auth/AuthProvider";
import type { Role } from "./auth/types";
import { CandidateHome } from "./candidate/CandidateHome";
import { ManagerCreateJdPage, ManagerHome, ManagerSchedulePage } from "./manager/ManagerHome";
import { AuthenticatedShell } from "./layout/AuthenticatedShell";
import { ProfilePage } from "./profile/ProfilePage";

const roleHomes: Record<Role, string> = {
  CANDIDATE: "/candidate",
  MANAGER: "/manager/jds",
  ADMIN: "/admin"
};

function UnknownRoute({ home }: { home: string }): React.JSX.Element {
  return (
    <main className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <FocusedHeading>Page unavailable</FocusedHeading>
      <p className="mt-3 text-slate-600">The requested page is not available.</p>
      <Link className="mt-4 inline-flex font-bold text-indigo-700 hover:underline" to={home}>Return to your home</Link>
    </main>
  );
}

function AuthenticatedRoutes({
  auth
}: {
  auth: AuthController & { status: "authenticated" };
}): React.JSX.Element {
  const home = roleHomes[auth.current.user.role];
  const protectedElement = (role: Role, element: React.ReactNode): React.JSX.Element => (
    <ProtectedRoute auth={auth} allowedRoles={[role]}>
      {element}
    </ProtectedRoute>
  );
  return (
    <Routes>
      <Route
        element={<AuthenticatedShell user={auth.current.user} onLogout={auth.logout} />}
      >
        <Route path="/" element={<Navigate to={home} replace />} />
        <Route path="/candidate" element={protectedElement("CANDIDATE", <CandidateHome />)} />
        <Route path="/manager" element={protectedElement("MANAGER", <Navigate to="/manager/jds" replace />)} />
        <Route path="/manager/jds" element={(
          <ProtectedRoute auth={auth} allowedRoles={["MANAGER", "ADMIN"]}>
            <ManagerHome access={auth.current.user.role === "ADMIN" ? "admin" : "manager"} />
          </ProtectedRoute>
        )} />
        <Route path="/manager/jds/new" element={(
          <ProtectedRoute auth={auth} allowedRoles={["MANAGER", "ADMIN"]}>
            <ManagerCreateJdPage />
          </ProtectedRoute>
        )} />
        <Route path="/manager/interviews/schedule" element={protectedElement("MANAGER", <ManagerSchedulePage />)} />
        <Route path="/admin" element={protectedElement("ADMIN", <AdminHome />)} />
        <Route path="/admin/organizations" element={protectedElement("ADMIN", <OrganizationsPage />)} />
        <Route path="/profile" element={<ProfilePage user={auth.current.user} />} />
        <Route path="*" element={<UnknownRoute home={home} />} />
      </Route>
    </Routes>
  );
}

export function App(): React.JSX.Element {
  const auth = useAuth();
  if (auth.status === "loading") return <p className="grid min-h-screen place-items-center bg-slate-950 font-semibold text-white" role="status">Loading your account…</p>;
  if (auth.status === "anonymous") return <LoginPage />;
  if (auth.status === "error" && auth.error.code === "SESSION_EXPIRED") {
    return <SessionExpiredPage reason="expired" />;
  }
  if (auth.status === "error" && auth.error.code === "SESSION_REVOKED") {
    return <SessionExpiredPage reason="revoked" />;
  }
  if (auth.status === "error") return <AccessErrorPage message={auth.error.message} />;
  return <AuthenticatedRoutes auth={auth} />;
}
