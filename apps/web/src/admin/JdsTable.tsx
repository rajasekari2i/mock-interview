import type { AdminJobDescription } from "./types";

export function JdsTable({ items }: { items: AdminJobDescription[] }): React.JSX.Element {
  if (!items.length) return <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-7 text-center text-slate-600">No job descriptions found.</p>;
  return <div className="overflow-x-auto rounded-xl border border-slate-200" tabIndex={0} aria-label="Application job descriptions"><table className="w-full min-w-3xl border-collapse">
    <caption className="p-4 text-left font-bold text-slate-800">Application job descriptions</caption><thead className="bg-slate-50"><tr>{["Title", "Creator", "Source", "Created"].map((label) => <th className="border-y border-slate-200 px-4 py-3 text-left text-xs tracking-wider text-slate-500 uppercase" scope="col" key={label}>{label}</th>)}</tr></thead>
    <tbody>{items.map((item) => <tr className="hover:bg-slate-50" key={item.id}><td className="border-b border-slate-100 px-4 py-4 font-semibold">{item.title}</td><td className="border-b border-slate-100 px-4 py-4 text-slate-600">{item.createdBy.displayName}</td><td className="border-b border-slate-100 px-4 py-4 text-slate-600">{item.sourceFormat ?? "Manual"}</td><td className="border-b border-slate-100 px-4 py-4 text-slate-600"><time dateTime={item.createdAt}>{item.createdAt.slice(0, 10)}</time></td></tr>)}</tbody>
  </table></div>;
}
