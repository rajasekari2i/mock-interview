import { FocusedHeading } from "../auth/FocusedHeading";
import type { CurrentUser } from "../auth/types";
import { ProfileImage } from "../components/ProfileImage";

export function ProfilePage({ user }: { user: CurrentUser }): React.JSX.Element {
  return (
    <section className="mx-auto max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <FocusedHeading>Your profile</FocusedHeading>
      <div className="my-7 inline-flex rounded-full ring-4 ring-indigo-50 [&>*]:size-24 [&>*]:text-2xl">
        <ProfileImage displayName={user.displayName} src={user.profilePictureUrl} />
      </div>
      <dl className="grid gap-4">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <dt className="text-xs font-bold tracking-wider text-slate-500 uppercase">Name</dt>
          <dd className="mt-1 font-semibold text-slate-900">{user.displayName}</dd>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <dt className="text-xs font-bold tracking-wider text-slate-500 uppercase">Email</dt>
          <dd className="mt-1 font-semibold text-slate-900">{user.email}</dd>
        </div>
      </dl>
    </section>
  );
}
