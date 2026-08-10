import type { ReactNode } from "react";

type AsyncStateProps = {
  children: ReactNode;
  error: string | null;
  loading: boolean;
  loadingMessage?: string;
  onRetry?: () => void;
};

export function AsyncState({
  children,
  error,
  loading,
  loadingMessage = "Loading",
  onRetry
}: AsyncStateProps) {
  if (loading) {
    return <p className="rounded-xl bg-indigo-50 p-4 font-semibold text-indigo-800" role="status">{loadingMessage}</p>;
  }
  if (error !== null) {
    return (
      <div className="rounded-xl border-l-4 border-rose-500 bg-rose-50 p-4 text-rose-800" role="alert">
        <p className="mb-3">{error}</p>
        {onRetry === undefined ? null : <button className="rounded-lg bg-rose-700 px-4 py-2 font-bold text-white hover:bg-rose-800" onClick={onRetry}>Retry</button>}
      </div>
    );
  }
  return <>{children}</>;
}
