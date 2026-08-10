import { Outlet } from "react-router-dom";

import type { CurrentUser } from "../auth/types";
import { RoleNavigation } from "../navigation/RoleNavigation";
import { ProfileMenu } from "./ProfileMenu";

export function AuthenticatedShell({
  user,
  onLogout
}: {
  user: CurrentUser;
  onLogout: () => Promise<void>;
}): React.JSX.Element {
  return (
    <div className="min-h-screen bg-[#f5f6f8] lg:grid lg:grid-cols-[248px_minmax(0,1fr)]">
      <a className="fixed -top-20 left-4 z-50 rounded-lg bg-white px-4 py-3 font-bold text-indigo-700 shadow-lg focus:top-4" href="#main-content">
        Skip to main content
      </a>
      <aside className="border-b border-slate-200 bg-white px-4 py-4 lg:sticky lg:top-0 lg:h-screen lg:border-r lg:border-b-0 lg:px-4 lg:py-6">
        <div className="flex min-w-0 items-center gap-3 px-2">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-violet-600 text-xs font-black text-white shadow-md shadow-violet-600/20" aria-hidden="true">MI</span>
          <span className="grid min-w-0 leading-tight">
            <strong className="truncate text-slate-950">MockInterview</strong>
            <small className="truncate text-xs font-semibold text-slate-500 capitalize">{user.role.toLowerCase()} workspace</small>
          </span>
        </div>
        <RoleNavigation role={user.role} />
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-40 flex min-h-16 items-center justify-end border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6 lg:px-8">
          <ProfileMenu user={user} onLogout={onLogout} />
        </header>
        <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8" id="main-content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
