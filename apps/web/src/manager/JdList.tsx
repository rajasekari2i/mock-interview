import type { ManagerJobDescription } from "./types";

export function JdList({ items }: { items: ManagerJobDescription[] }): React.JSX.Element {
  if (items.length === 0) return <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-7 text-center text-slate-600">You have not created any job descriptions yet.</p>;
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200" tabIndex={0} aria-label="Your job descriptions table">
      <table className="w-full min-w-2xl border-collapse bg-white">
        <caption className="p-4 text-left font-bold text-slate-800">Your job descriptions</caption>
        <thead className="bg-slate-50">
          <tr>
            <th className="border-y border-slate-200 px-4 py-3 text-left text-xs tracking-wider text-slate-500 uppercase" scope="col">Title</th>
            <th className="border-y border-slate-200 px-4 py-3 text-left text-xs tracking-wider text-slate-500 uppercase" scope="col">Source</th>
            <th className="border-y border-slate-200 px-4 py-3 text-left text-xs tracking-wider text-slate-500 uppercase" scope="col">Created</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr className="hover:bg-slate-50" key={item.id}>
              <td className="border-b border-slate-100 px-4 py-4 font-semibold">{item.title}</td>
              <td className="border-b border-slate-100 px-4 py-4 text-slate-600">{item.sourceType === "MANUAL" ? "Manual" : `${String(item.sourceFormat)} upload`}</td>
              <td className="border-b border-slate-100 px-4 py-4 text-slate-600"><time dateTime={item.createdAt}>{item.createdAt.slice(0, 10)}</time></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
