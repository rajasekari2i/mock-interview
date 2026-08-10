import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { FocusedHeading } from "../auth/FocusedHeading";
import { fetchAdminJds } from "../admin/api";
import { JdForms } from "./JdForms";
import { JdList } from "./JdList";
import { ScheduleInterviewForm } from "./ScheduleInterviewForm";
import { ScheduledInterviewList } from "./ScheduledInterviewList";
import {
  fetchManagerCandidates,
  fetchManagerInterviews,
  fetchManagerJobDescriptions
} from "./api";
import type { ManagerCandidate, ManagerInterview, ManagerJobDescription } from "./types";

function PageHeading({ title, description }: { title: string; description: string }): React.JSX.Element {
  return (
    <div>
      <FocusedHeading>{title}</FocusedHeading>
      <p className="mt-2 text-slate-600">{description}</p>
    </div>
  );
}

export function ManagerHome({ access = "manager" }: { access?: "manager" | "admin" }): React.JSX.Element {
  const [items, setItems] = useState<ManagerJobDescription[] | null>(null);
  const [failed, setFailed] = useState(false);
  const load = useCallback((): void => {
    setFailed(false);
    setItems(null);
    const request = access === "admin" ? fetchAdminJds(1) : fetchManagerJobDescriptions();
    void request
      .then((page) => { setItems(page.items); })
      .catch(() => { setFailed(true); });
  }, [access]);
  useEffect(load, [load]);

  return (
    <section>
      <div className="mb-7 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <PageHeading title="Job descriptions" description={access === "admin" ? "Review job descriptions created across the application." : "Manage the job descriptions you created for candidate interviews."} />
        <Link className="inline-flex shrink-0 items-center justify-center rounded-xl bg-slate-900 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-violet-700" to="/manager/jds/new">Create job description</Link>
      </div>
      {items === null && !failed ? <p className="rounded-xl bg-violet-50 p-4 font-semibold text-violet-800" role="status">Loading job descriptions…</p> : null}
      {failed ? <div className="rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">Job descriptions could not load. <button className="ml-3 rounded-lg bg-rose-700 px-4 py-2 font-bold text-white" type="button" onClick={load}>Retry</button></div> : null}
      {items !== null ? <JdList items={items} /> : null}
    </section>
  );
}

export function ManagerCreateJdPage(): React.JSX.Element {
  return (
    <section className="max-w-4xl">
      <Link className="mb-5 inline-flex items-center gap-2 text-sm font-bold text-violet-700 hover:underline" to="/manager/jds"><span aria-hidden="true">←</span> Back to job descriptions</Link>
      <PageHeading title="Create job description" description="Choose manual entry or upload a supported document in the same form." />
      <div className="mt-7"><JdForms onCreated={() => undefined} /></div>
    </section>
  );
}

export function ManagerSchedulePage(): React.JSX.Element {
  const [candidates, setCandidates] = useState<ManagerCandidate[] | null>(null);
  const [items, setItems] = useState<ManagerJobDescription[] | null>(null);
  const [interviews, setInterviews] = useState<ManagerInterview[] | null>(null);
  useEffect(() => {
    void Promise.all([
      fetchManagerCandidates(),
      fetchManagerJobDescriptions(),
      fetchManagerInterviews()
    ]).then(([candidatePage, jdPage, interviewPage]) => {
      setCandidates(candidatePage.items);
      setItems(jdPage.items);
      setInterviews(interviewPage.items);
    }).catch(() => {
      setCandidates([]);
      setItems([]);
      setInterviews([]);
    });
  }, []);
  const loading = candidates === null || items === null || interviews === null;
  const loadedInterviews = interviews ?? [];

  return (
    <section>
      <PageHeading title="Schedule interview" description="Allocate one of your job descriptions to an active candidate." />
      {loading ? <p className="mt-7 rounded-xl bg-violet-50 p-4 font-semibold text-violet-800" role="status">Loading scheduling choices…</p> : (
        <>
          <ScheduleInterviewForm candidates={candidates} jobDescriptions={items} onScheduled={(created) => { setInterviews([created, ...loadedInterviews]); }} />
          <h2 className="mt-9 mb-4 text-2xl font-extrabold tracking-tight text-slate-900">Scheduled interviews</h2>
          <ScheduledInterviewList items={loadedInterviews} />
        </>
      )}
    </section>
  );
}
