import { useCallback, useEffect, useState } from "react";

import { FocusedHeading } from "../auth/FocusedHeading";
import { fetchCandidateInterviews } from "./api";
import type { CandidateInterviewPage } from "./types";

type ViewState =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "ready"; page: CandidateInterviewPage };

const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  timeZone: "UTC"
});
const timeFormatter = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: "UTC"
});

export function CandidateHome(): React.JSX.Element {
  const [state, setState] = useState<ViewState>({ kind: "loading" });
  const load = useCallback((): void => {
    setState({ kind: "loading" });
    void fetchCandidateInterviews()
      .then((page) => {
        setState({ kind: "ready", page });
      })
      .catch(() => {
        setState({ kind: "error" });
      });
  }, []);
  useEffect(load, [load]);

  return (
    <section>
      <div className="mb-7">
        <FocusedHeading>Your allocated interviews</FocusedHeading>
        <p className="mt-2 text-slate-600">Review the interviews currently assigned to you.</p>
      </div>
      {state.kind === "loading" ? <p className="rounded-xl bg-indigo-50 p-4 font-semibold text-indigo-800" role="status">Loading interviews…</p> : null}
      {state.kind === "error" ? (
        <div className="rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">
          <p className="mb-3">Interviews could not load. Try again.</p>
          <button className="rounded-lg bg-rose-700 px-4 py-2 font-bold text-white hover:bg-rose-800" type="button" onClick={load}>
            Retry
          </button>
        </div>
      ) : null}
      {state.kind === "ready" && state.page.items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-600">No interviews have been allocated yet.</p>
      ) : null}
      {state.kind === "ready" && state.page.items.length > 0 ? (
        <ul className="grid list-none gap-4" aria-label="Allocated interviews">
          {state.page.items.map((interview) => {
                const scheduled = new Date(interview.scheduledAt);
                return (
                  <li className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md sm:p-6" key={interview.id}>
                    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                      <div>
                        <p className="mb-1 text-xs font-bold tracking-wider text-slate-400 uppercase">Job description</p>
                        <h2 className="text-xl font-bold text-slate-900">{interview.jobDescription.title}</h2>
                      </div>
                      <span className="inline-flex self-start rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700 ring-1 ring-emerald-200">{interview.status}</span>
                    </div>
                    <dl className="mt-5 grid gap-4 border-t border-slate-100 pt-5 sm:grid-cols-2">
                      <div><dt className="text-xs font-bold tracking-wider text-slate-400 uppercase">Scheduled date</dt><dd className="mt-1 font-semibold text-slate-700"><time dateTime={interview.scheduledAt}>{dateFormatter.format(scheduled)}</time></dd></div>
                      <div><dt className="text-xs font-bold tracking-wider text-slate-400 uppercase">Scheduled time</dt><dd className="mt-1 font-semibold text-slate-700"><time dateTime={interview.scheduledAt}>{timeFormatter.format(scheduled)} UTC</time></dd></div>
                    </dl>
                  </li>
                );
          })}
        </ul>
      ) : null}
    </section>
  );
}
