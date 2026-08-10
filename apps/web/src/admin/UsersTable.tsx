import type { AdminUser } from "./types";

export function UsersTable({ items, onDetails }: { items: AdminUser[]; onDetails: (user: AdminUser) => void }): React.JSX.Element {
  if (!items.length) return <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-7 text-center text-slate-600">No users found.</p>;
  return <div className="overflow-x-auto rounded-xl border border-slate-200" tabIndex={0} aria-label="Application users">
    <table className="w-full min-w-4xl border-collapse"><caption className="p-4 text-left font-bold text-slate-800">Application users</caption><thead className="bg-slate-50"><tr>{["Name", "Email", "Role", "Status", "Details"].map((label) => <th className="border-y border-slate-200 px-4 py-3 text-left text-xs tracking-wider text-slate-500 uppercase" scope="col" key={label}>{label}</th>)}</tr></thead>
      <tbody>{items.map((item) => <tr className="hover:bg-slate-50" key={item.id}><td className="border-b border-slate-100 px-4 py-4 font-semibold">{item.displayName}</td><td className="border-b border-slate-100 px-4 py-4 text-slate-600">{item.email}</td><td className="border-b border-slate-100 px-4 py-4"><span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-bold text-indigo-700">{item.role}</span></td><td className="border-b border-slate-100 px-4 py-4"><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">{item.status}</span></td><td className="border-b border-slate-100 px-4 py-4"><button className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50" type="button" onClick={() => { onDetails(item); }}>View details for {item.displayName}</button></td></tr>)}</tbody>
    </table>
  </div>;
}
