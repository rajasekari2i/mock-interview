import { useCallback, useEffect, useState } from "react";

import { FocusedHeading } from "../auth/FocusedHeading";
import { Pagination } from "../components/Pagination";
import { fetchAdminUser, fetchAdminUsers } from "./api";
import type { AdminUser, Page } from "./types";
import { UserDetailsDialog } from "./UserDetailsDialog";
import { UsersTable } from "./UsersTable";

function initialPage(name: string): number {
  const value = Number(new URLSearchParams(window.location.search).get(name) ?? "1");
  return Number.isInteger(value) && value > 0 ? value : 1;
}

function setQueryPage(name: string, page: number): void {
  const query = new URLSearchParams(window.location.search);
  query.set(name, String(page));
  window.history.replaceState(null, "", `${window.location.pathname}?${query.toString()}`);
}

export function AdminHome(): React.JSX.Element {
  const [usersPage, setUsersPage] = useState(() => initialPage("usersPage"));
  const [users, setUsers] = useState<Page<AdminUser> | null>(null);
  const [usersFailed, setUsersFailed] = useState(false);
  const [selected, setSelected] = useState<AdminUser | null>(null);
  const [detailsFailed, setDetailsFailed] = useState(false);

  const loadUsers = useCallback(() => {
    setUsersFailed(false);
    void fetchAdminUsers(usersPage).then(setUsers).catch(() => { setUsersFailed(true); });
  }, [usersPage]);
  useEffect(loadUsers, [loadUsers]);
  return <section>
    <div className="mb-7 rounded-2xl bg-slate-900 p-6 text-white shadow-lg [&_h1]:text-white sm:p-8">
    <FocusedHeading>Application administration</FocusedHeading>
    <p className="mt-2 mb-0 text-slate-300">Manage application users and their assigned roles.</p>
    </div>
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><h2 className="mb-4 text-2xl font-extrabold text-slate-900">Users</h2>
      {users === null && !usersFailed ? <p className="rounded-xl bg-indigo-50 p-4 font-semibold text-indigo-800" role="status">Loading users…</p> : null}
      {usersFailed ? <p className="rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">Users could not load. <button className="ml-3 rounded-lg bg-rose-700 px-4 py-2 font-bold text-white" type="button" onClick={loadUsers}>Retry</button></p> : null}
      {users ? <><UsersTable items={users.items} onDetails={(summary) => {
        setDetailsFailed(false);
        void fetchAdminUser(summary.id).then(setSelected).catch(() => { setDetailsFailed(true); });
      }} /><Pagination label="User pagination" page={users.page} totalPages={users.totalPages} totalItems={users.totalItems} onPage={(page) => { setQueryPage("usersPage", page); setUsersPage(page); }} /></> : null}
      {detailsFailed ? <p className="rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">User details could not load.</p> : null}
    </section>
    {selected ? <UserDetailsDialog user={selected} onClose={() => { setSelected(null); }} onSaved={(updated) => {
      setSelected(updated);
      setUsers((current) => {
        const page = current as Page<AdminUser>;
        return { ...page, items: page.items.map((item) => item.id === updated.id ? updated : item) };
      });
    }} /> : null}
  </section>;
}
