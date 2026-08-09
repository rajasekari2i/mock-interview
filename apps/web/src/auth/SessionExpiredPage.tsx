import { useEffect, useRef } from "react";

export function SessionExpiredPage({ reason }: { reason: "expired" | "revoked" }): React.JSX.Element {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  return (
    <main>
      <h1 ref={heading} tabIndex={-1}>
        Your session ended
      </h1>
      <p role="alert">
        {reason === "expired"
          ? "Your session expired for your security."
          : "Your access changed and this session was closed."}
      </p>
      <a href="/api/v1/auth/google/login">Sign in again</a>
    </main>
  );
}
