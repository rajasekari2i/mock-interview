import type { ManagerInterview } from "./types";

export function ScheduledInterviewList({ items }: { items: ManagerInterview[] }): React.JSX.Element {
  if (items.length === 0) return <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-7 text-center text-slate-600">You have not scheduled any interviews yet.</p>;
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200" tabIndex={0} aria-label="Scheduled interview history">
      <table className="w-full min-w-3xl border-collapse bg-white">
        <caption className="p-4 text-left font-bold text-slate-800">Your scheduled interviews</caption>
        <thead className="bg-slate-50"><tr><th className="border-y border-slate-200 px-4 py-3 text-left text-xs tracking-wider text-slate-500 uppercase">Candidate</th><th className="border-y border-slate-200 px-4 py-3 text-left text-xs tracking-wider text-slate-500 uppercase">JD</th><th className="border-y border-slate-200 px-4 py-3 text-left text-xs tracking-wider text-slate-500 uppercase">Date and time</th><th className="border-y border-slate-200 px-4 py-3 text-left text-xs tracking-wider text-slate-500 uppercase">Status</th></tr></thead>
        <tbody>{items.map((item) => (
          <tr className="hover:bg-slate-50" key={item.id}>
            <td className="border-b border-slate-100 px-4 py-4 font-semibold">{item.candidate.displayName}</td>
            <td className="border-b border-slate-100 px-4 py-4 text-slate-600">{item.jobDescription.title}</td>
            <td className="border-b border-slate-100 px-4 py-4 text-slate-600"><time dateTime={item.scheduledAt}>{new Date(item.scheduledAt).toLocaleString()}</time></td>
            <td className="border-b border-slate-100 px-4 py-4"><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700 ring-1 ring-emerald-200">{item.status}</span></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}
