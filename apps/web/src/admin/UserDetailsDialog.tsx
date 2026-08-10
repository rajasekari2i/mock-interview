import { useEffect, useRef, useState } from "react";

import type { Role } from "../auth/types";
import { saveAdminUserRole } from "./api";
import type { AdminUser } from "./types";

interface Props {
  user: AdminUser;
  onClose: () => void;
  onSaved: (user: AdminUser) => void;
}

export function UserDetailsDialog({ user, onClose, onSaved }: Props): React.JSX.Element {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);
  const [role, setRole] = useState<Role>(user.role);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ error: boolean; text: string } | null>(null);
  useEffect(() => {
    openerRef.current = document.activeElement as HTMLElement;
    (dialogRef.current as HTMLDialogElement).showModal();
  }, []);
  const close = (): void => {
    (dialogRef.current as HTMLDialogElement).close();
    onClose();
    openerRef.current?.focus();
  };
  return <dialog
    className="m-auto w-[min(36rem,calc(100vw-2rem))] rounded-2xl border border-slate-200 bg-white p-6 text-slate-900 shadow-2xl sm:p-8"
    ref={dialogRef}
    aria-labelledby="user-details-title"
    onCancel={(event) => { event.preventDefault(); close(); }}
  >
    <h2 className="mb-5 text-2xl font-extrabold text-slate-950" id="user-details-title">User details</h2>
    <dl className="mb-5 grid gap-3">
      <div className="rounded-xl bg-slate-50 p-4"><dt className="text-xs font-bold tracking-wider text-slate-500 uppercase">Name</dt><dd className="mt-1 font-semibold">{user.displayName}</dd></div>
      <div className="rounded-xl bg-slate-50 p-4"><dt className="text-xs font-bold tracking-wider text-slate-500 uppercase">Email</dt><dd className="mt-1 font-semibold">{user.email}</dd></div>
      <div className="rounded-xl bg-slate-50 p-4"><dt className="text-xs font-bold tracking-wider text-slate-500 uppercase">Status</dt><dd className="mt-1 font-semibold">{user.status}</dd></div>
    </dl>
    <label className="mb-5 grid gap-2 text-sm font-bold text-slate-700">Role<select className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 font-normal" value={role} disabled={busy} onChange={(event) => { setRole(event.target.value as Role); }}>
      <option value="CANDIDATE">Candidate</option><option value="MANAGER">Manager</option><option value="ADMIN">Admin</option>
    </select></label>
    <div className="flex flex-wrap gap-3"><button className="rounded-lg bg-indigo-600 px-5 py-2.5 font-bold text-white hover:bg-indigo-700 disabled:opacity-50" type="button" disabled={busy} onClick={() => {
      setBusy(true); setMessage(null);
      void saveAdminUserRole(user.id, role).then((updated) => {
        onSaved(updated); setMessage({ error: false, text: "Role updated." });
      }).catch(() => { setMessage({ error: true, text: "Role could not be updated." }); })
        .finally(() => { setBusy(false); });
    }}>Save role</button>
    <button className="rounded-lg border border-slate-300 bg-white px-5 py-2.5 font-bold text-slate-700 hover:bg-slate-50" type="button" onClick={close}>Close</button></div>
    {message?.error ? <p className="mt-4 rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">{message.text}</p> : null}
    {message && !message.error ? <p className="mt-4 rounded-xl bg-emerald-50 p-4 font-semibold text-emerald-800" role="status">{message.text}</p> : null}
  </dialog>;
}
