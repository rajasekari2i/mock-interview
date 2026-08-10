import { useEffect, useRef } from "react";

export function SessionExpiredPage({ reason }: { reason: "expired" | "revoked" }): React.JSX.Element {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10">
      <section className="w-full max-w-md rounded-3xl bg-white p-8 shadow-2xl">
      <h1 className="text-3xl font-extrabold tracking-tight text-slate-950" ref={heading} tabIndex={-1}>
        Your session ended
      </h1>
      <p className="my-6 rounded-xl border-l-4 border-amber-500 bg-amber-50 p-4 text-amber-900" role="alert">
        {reason === "expired"
          ? "Your session expired for your security."
          : "Your access changed and this session was closed."}
      </p>
      <a className="inline-flex items-center rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white no-underline shadow-md hover:bg-indigo-700" href="/api/v1/auth/google/login">Sign in again</a>
      </section>
    </main>
  );
}
