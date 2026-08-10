import { useCallback, useEffect, useState } from "react";

import { FocusedHeading } from "../auth/FocusedHeading";
import { createAdminOrganization, fetchAdminOrganizations } from "./api";
import type { Organization } from "./types";

export function OrganizationsPage(): React.JSX.Element {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<"success" | "error" | null>(null);
  const load = useCallback((): void => {
    setLoading(true);
    setLoadFailed(false);
    void fetchAdminOrganizations()
      .then((response) => { setOrganizations(response.items); })
      .catch(() => { setLoadFailed(true); })
      .finally(() => { setLoading(false); });
  }, []);

  useEffect(load, [load]);

  return (
    <section>
      <div className="mb-7 rounded-2xl bg-slate-900 p-6 text-white shadow-lg [&_h1]:text-white sm:p-8">
        <FocusedHeading>Organizations</FocusedHeading>
        <p className="mt-2 mb-0 text-slate-300">Create and review organizations that can use MockInterview.</p>
      </div>
      <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(18rem,0.75fr)_minmax(0,1.25fr)]">
        <form
          className="min-w-0 self-start rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
          onSubmit={(event) => {
            event.preventDefault();
            const form = event.currentTarget;
            setBusy(true);
            setMessage(null);
            void createAdminOrganization(
              (form.elements.namedItem("name") as HTMLInputElement).value,
              (form.elements.namedItem("slug") as HTMLInputElement).value
            ).then((created) => {
              setOrganizations((current) => [created, ...current]);
              form.reset();
              setMessage("success");
            }).catch(() => { setMessage("error"); })
              .finally(() => { setBusy(false); });
          }}
        >
          <h2 className="mb-2 text-xl font-extrabold text-slate-950">Create organization</h2>
          <p className="mb-5 text-sm text-slate-600">New organizations are active immediately.</p>
          <label className="mb-4 grid gap-2 text-sm font-bold text-slate-700">
            Organization name
            <input className="rounded-lg border border-slate-300 px-3 py-2.5 font-normal" name="name" required maxLength={200} />
          </label>
          <label className="mb-2 grid gap-2 text-sm font-bold text-slate-700">
            Organization slug
            <input className="rounded-lg border border-slate-300 px-3 py-2.5 font-normal" name="slug" required maxLength={100} pattern="[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*" aria-describedby="slug-help" />
          </label>
          <p className="mb-5 text-xs text-slate-500" id="slug-help">Use letters, numbers, and single hyphens.</p>
          <button className="rounded-lg bg-indigo-600 px-5 py-2.5 font-bold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50" type="submit" disabled={busy}>Create organization</button>
          {message === "success" ? <p className="mt-4 rounded-xl bg-emerald-50 p-4 font-semibold text-emerald-800" role="status">Organization created.</p> : null}
          {message === "error" ? <p className="mt-4 rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">Organization could not be created. Check that the slug is unique.</p> : null}
        </form>
        <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="mb-5 text-xl font-extrabold text-slate-950">Existing organizations</h2>
          {loading ? <p className="rounded-xl bg-indigo-50 p-4 font-semibold text-indigo-800" role="status">Loading organizations…</p> : null}
          {loadFailed ? <div className="rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">Organizations could not load. <button className="ml-3 rounded-lg bg-rose-700 px-4 py-2 font-bold text-white" type="button" onClick={load}>Retry</button></div> : null}
          {!loading && !loadFailed && organizations.length === 0 ? <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-7 text-center text-slate-600">No organizations found.</p> : null}
          {organizations.length > 0 ? (
            <div className="max-w-full overflow-x-auto rounded-xl border border-slate-200" tabIndex={0} aria-label="Organizations table">
              <table className="w-full min-w-xl border-collapse">
                <caption className="p-4 text-left font-bold text-slate-800">Application organizations</caption>
                <thead className="bg-slate-50"><tr>{["Name", "Slug", "Status"].map((label) => <th className="border-y border-slate-200 px-4 py-3 text-left text-xs tracking-wider text-slate-500 uppercase" scope="col" key={label}>{label}</th>)}</tr></thead>
                <tbody>{organizations.map((organization) => <tr className="hover:bg-slate-50" key={organization.id}><td className="border-b border-slate-100 px-4 py-4 font-semibold">{organization.name}</td><td className="border-b border-slate-100 px-4 py-4 font-mono text-sm text-slate-600">{organization.slug}</td><td className="border-b border-slate-100 px-4 py-4"><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">{organization.status}</span></td></tr>)}</tbody>
              </table>
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
}
