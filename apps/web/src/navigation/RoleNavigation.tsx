import type { Role } from "../auth/types";

const entries: Record<Role, readonly [string, string][]> = {
  CANDIDATE: [["Allocated interviews", "/candidate/interviews"]],
  MANAGER: [
    ["Job descriptions", "/manager/job-descriptions"],
    ["Candidate allocations", "/manager/allocations"],
    ["Managed readiness", "/manager/readiness"]
  ],
  ADMIN: [
    ["Manage users", "/admin/users"],
    ["Application reports", "/admin/reports"]
  ]
};

export function RoleNavigation({ role }: { role: Role }): React.JSX.Element {
  return (
    <nav aria-label="Role navigation">
      <ul>
        {entries[role].map(([label, href]) => (
          <li key={href}>
            <a href={href}>{label}</a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
