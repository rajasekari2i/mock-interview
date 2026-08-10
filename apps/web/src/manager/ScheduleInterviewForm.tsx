import { useRef, useState } from "react";

import { scheduleInterview } from "./api";
import type { ManagerCandidate, ManagerInterview, ManagerJobDescription } from "./types";

interface Props {
  candidates: ManagerCandidate[];
  jobDescriptions: ManagerJobDescription[];
  onScheduled: (interview: ManagerInterview) => void;
}

export function ScheduleInterviewForm({ candidates, jobDescriptions, onScheduled }: Props): React.JSX.Element {
  const [candidateId, setCandidateId] = useState("");
  const [jobDescriptionId, setJobDescriptionId] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const busyRef = useRef(false);
  const intent = useRef<{ payload: string; key: string } | null>(null);

  const change = (setter: (value: string) => void, value: string): void => {
    setter(value);
    intent.current = null;
  };
  const unavailable = candidates.length === 0 || jobDescriptions.length === 0;
  return (
    <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="mb-2 text-xl font-extrabold text-slate-900">Schedule an interview</h2>
      {unavailable ? <p className="mb-5 text-slate-600">An active candidate and one of your JDs are required.</p> : null}
      <form className="grid gap-4 md:grid-cols-2" onSubmit={(event) => {
        event.preventDefault();
        if (busyRef.current) return;
        if (!candidateId || !jobDescriptionId || !date || !time) {
          setMessage({ kind: "error", text: "Choose a candidate, JD, date, and time." });
          return;
        }
        const scheduledAt = new Date(`${date}T${time}`).toISOString();
        if (new Date(scheduledAt).getTime() <= Date.now()) {
          setMessage({ kind: "error", text: "Choose a future date and time." });
          return;
        }
        const payload = `${candidateId}|${jobDescriptionId}|${scheduledAt}`;
        if (intent.current?.payload !== payload) intent.current = { payload, key: crypto.randomUUID() };
        const key = intent.current.key;
        busyRef.current = true;
        setBusy(true);
        setMessage(null);
        void scheduleInterview(candidateId, jobDescriptionId, scheduledAt, key)
          .then((created) => {
            intent.current = null;
            setMessage({ kind: "success", text: "Interview scheduled." });
            onScheduled(created);
          })
          .catch((error: unknown) => {
            const status = typeof error === "object" && error !== null && "message" in error
              ? String((error as { message: unknown }).message)
              : "";
            setMessage({
              kind: "error",
              text: status.includes("409")
                ? "This request key was already used for another interview."
                : "Interview could not be scheduled. Try again."
            });
          })
          .finally(() => { busyRef.current = false; setBusy(false); });
      }}>
        <label className="grid gap-2 text-sm font-bold text-slate-700">Candidate<select className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 font-normal disabled:bg-slate-100" value={candidateId} onChange={(event) => { change(setCandidateId, event.target.value); }} disabled={unavailable || busy}>
          <option value="">Choose a candidate</option>
          {candidates.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.displayName} ({candidate.email})</option>)}
        </select></label>
        <label className="grid gap-2 text-sm font-bold text-slate-700">Job description<select className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 font-normal disabled:bg-slate-100" value={jobDescriptionId} onChange={(event) => { change(setJobDescriptionId, event.target.value); }} disabled={unavailable || busy}>
          <option value="">Choose a JD</option>
          {jobDescriptions.map((jd) => <option key={jd.id} value={jd.id}>{jd.title}</option>)}
        </select></label>
        <label className="grid gap-2 text-sm font-bold text-slate-700">Interview date<input className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 font-normal disabled:bg-slate-100" type="date" value={date} onChange={(event) => { change(setDate, event.target.value); }} disabled={unavailable || busy} /></label>
        <label className="grid gap-2 text-sm font-bold text-slate-700">Interview time<input className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 font-normal disabled:bg-slate-100" type="time" value={time} onChange={(event) => { change(setTime, event.target.value); }} disabled={unavailable || busy} /></label>
        <button className="rounded-lg bg-indigo-600 px-5 py-2.5 font-bold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50 md:col-span-2 md:justify-self-start" type="submit" disabled={unavailable || busy}>Schedule interview</button>
      </form>
      {message?.kind === "error" ? <p className="mt-4 rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">{message.text}</p> : null}
      {message?.kind === "success" ? <p className="mt-4 rounded-xl bg-emerald-50 p-4 font-semibold text-emerald-800" role="status">{message.text}</p> : null}
    </section>
  );
}
