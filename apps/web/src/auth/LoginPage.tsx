import { FocusedHeading } from "./FocusedHeading";

export function LoginPage(): React.JSX.Element {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10 sm:px-6">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-7 shadow-2xl shadow-slate-950/30 sm:p-10">
        <div className="mb-10 flex items-center gap-3 text-lg font-extrabold text-slate-950">
          <span className="grid size-11 place-items-center rounded-2xl bg-indigo-600 text-sm font-black text-white shadow-lg shadow-indigo-600/25" aria-hidden="true">MI</span>
          <span>MockInterview</span>
        </div>
        <p className="mb-2 text-xs font-extrabold tracking-[0.18em] text-indigo-600 uppercase">Welcome back</p>
        <FocusedHeading>Sign in to MockInterview</FocusedHeading>
        <p className="mt-3 mb-8 text-base leading-7 text-slate-600">Use your approved work Google account to continue to your workspace.</p>
        <a className="flex w-full items-center justify-center gap-3 rounded-xl border border-slate-300 bg-white px-4 py-3 font-bold text-slate-700 no-underline shadow-sm transition hover:border-indigo-300 hover:bg-indigo-50 hover:shadow-md" href="/api/v1/auth/google/login">
          <span className="text-lg font-black text-blue-500" aria-hidden="true">G</span>
          Continue with Google
        </a>
        <p className="mt-5 mb-0 text-center text-xs text-slate-600">Secure access powered by Google OAuth</p>
      </section>
    </main>
  );
}

export function AccessErrorPage({ message }: { message: string }): React.JSX.Element {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10 sm:px-6">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-7 shadow-2xl shadow-slate-950/30 sm:p-10">
        <div className="mb-10 flex items-center gap-3 text-lg font-extrabold text-slate-950">
          <span className="grid size-11 place-items-center rounded-2xl bg-indigo-600 text-sm font-black text-white" aria-hidden="true">MI</span>
          <span>MockInterview</span>
        </div>
        <p className="mb-2 text-xs font-extrabold tracking-[0.18em] text-rose-600 uppercase">Sign-in issue</p>
        <FocusedHeading>Access unavailable</FocusedHeading>
        <p className="my-6 rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">{message}</p>
        <a className="inline-flex items-center font-bold text-indigo-700 underline-offset-4 hover:underline" href="/">Return to sign in</a>
      </section>
    </main>
  );
}
