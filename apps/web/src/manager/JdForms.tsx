import { useRef, useState } from "react";

import { createManualJobDescription, uploadJobDescription } from "./api";
import type { ManagerJobDescription } from "./types";

const acceptedExtensions = /\.(pdf|docx|txt)$/iu;

export function JdForms({ onCreated }: { onCreated: (created: ManagerJobDescription) => void }): React.JSX.Element {
  const [mode, setMode] = useState<"manual" | "upload">("manual");
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [message, setMessage] = useState<"success" | "error" | null>(null);

  const submit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (busyRef.current) return;
    const form = event.currentTarget;
    const title = (form.elements.namedItem("title") as HTMLInputElement).value;
    const document = (form.elements.namedItem("document") as HTMLInputElement | null)?.files?.[0];
    if (mode === "upload" && (document === undefined || !acceptedExtensions.test(document.name))) {
      setMessage("error");
      return;
    }
    busyRef.current = true;
    setBusy(true);
    setMessage(null);
    try {
      const created = mode === "manual"
        ? await createManualJobDescription(title, (form.elements.namedItem("content") as HTMLTextAreaElement).value)
        : await uploadJobDescription(title, document as File);
      form.reset();
      onCreated(created);
      setMessage("success");
    } catch {
      setMessage("error");
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 p-5 sm:p-6">
        <h2 className="text-xl font-extrabold text-slate-900">JD details</h2>
        <p className="mt-1 text-sm text-slate-500">Add the content manually or upload an existing document.</p>
        <div className="mt-5 inline-flex rounded-xl bg-slate-100 p-1" aria-label="Creation method">
          <button className={`rounded-lg px-4 py-2 text-sm font-bold ${mode === "manual" ? "bg-white text-violet-700 shadow-sm" : "text-slate-600"}`} type="button" onClick={() => { setMode("manual"); setMessage(null); }}>Manual text</button>
          <button className={`rounded-lg px-4 py-2 text-sm font-bold ${mode === "upload" ? "bg-white text-violet-700 shadow-sm" : "text-slate-600"}`} type="button" onClick={() => { setMode("upload"); setMessage(null); }}>Upload document</button>
        </div>
      </div>
      <form aria-label="Create job description form" className="grid gap-5 p-5 sm:p-6" onSubmit={(event) => void submit(event)}>
        <label className="grid gap-2 text-sm font-bold text-slate-700">JD title<input className="rounded-xl border border-slate-300 px-3 py-2.5 font-normal focus:border-violet-500" name="title" required maxLength={200} /></label>
        {mode === "manual" ? (
          <label className="grid gap-2 text-sm font-bold text-slate-700">Job description content<textarea className="min-h-56 resize-y rounded-xl border border-slate-300 px-3 py-2.5 font-normal focus:border-violet-500" name="content" required maxLength={100000} placeholder="Paste the responsibilities, experience, and skills for this role…" /></label>
        ) : (
          <div>
            <label className="grid gap-2 text-sm font-bold text-slate-700">JD document<input className="w-full rounded-xl border border-dashed border-slate-300 bg-slate-50 px-3 py-4 font-normal file:mr-3 file:rounded-lg file:border-0 file:bg-violet-100 file:px-4 file:py-2 file:font-bold file:text-violet-700" name="document" type="file" accept=".pdf,.docx,.txt" /></label>
            <p className="mt-2 text-sm text-slate-500">PDF, DOCX, or TXT up to 5 MiB.</p>
          </div>
        )}
        <div className="flex flex-wrap items-center gap-4 border-t border-slate-100 pt-5">
          <button className="rounded-xl bg-slate-900 px-5 py-2.5 font-bold text-white shadow-sm hover:bg-violet-700 disabled:opacity-50" type="submit" disabled={busy}>{mode === "manual" ? "Create job description" : "Upload job description"}</button>
          {message === "success" ? <p className="font-semibold text-emerald-700" role="status">Job description created.</p> : null}
          {message === "error" ? <p className="text-rose-700" role="alert">Job description could not be created. Choose a valid PDF, DOCX, or TXT and try again.</p> : null}
        </div>
      </form>
    </div>
  );
}
