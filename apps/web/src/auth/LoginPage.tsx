import { FocusedHeading } from "./FocusedHeading";

export function LoginPage(): React.JSX.Element {
  return (
    <main>
      <FocusedHeading>Sign in to MockInterview</FocusedHeading>
      <p>Use your approved work Google account.</p>
      <a href="/api/v1/auth/google/login">Continue with Google</a>
    </main>
  );
}

export function AccessErrorPage({ message }: { message: string }): React.JSX.Element {
  return (
    <main>
      <FocusedHeading>Access unavailable</FocusedHeading>
      <p role="alert">{message}</p>
    </main>
  );
}
