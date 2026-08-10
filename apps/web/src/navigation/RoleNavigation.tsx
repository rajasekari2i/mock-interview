import type { Role } from "../auth/types";
import { NavLink } from "react-router-dom";

const entries: Record<Role, readonly [string, string][]> = {
  CANDIDATE: [["My interviews", "/candidate"]],
  MANAGER: [["Job descriptions", "/manager/jds"], ["Schedule interview", "/manager/interviews/schedule"]],
  ADMIN: [["Users", "/admin"], ["Job descriptions", "/manager/jds"], ["Organizations", "/admin/organizations"]]
};

export function RoleNavigation({ role }: { role: Role }): React.JSX.Element {
  return (
    <nav className="mt-7" aria-label="Role navigation">
      <p className="mb-2 px-3 text-[11px] font-bold tracking-[0.16em] text-slate-600 uppercase">Workspace</p>
      <ul className="grid list-none grid-cols-2 gap-1 lg:flex lg:flex-col">
        {entries[role].map(([label, href]) => (
          <li className="min-w-0" key={href}>
            <NavLink
              className={({ isActive }) => `group flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-semibold no-underline transition ${isActive ? "bg-violet-50 text-violet-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"}`}
              end={href === "/admin" || href === "/manager/jds"}
              to={href}
            >
              <span className="grid size-8 shrink-0 place-items-center rounded-lg border border-slate-200 bg-white text-xs font-black text-violet-600 shadow-sm group-hover:border-violet-200" aria-hidden="true">{label.slice(0, 1)}</span>
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
