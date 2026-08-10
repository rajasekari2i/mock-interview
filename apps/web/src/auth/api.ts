import { decodeCurrentUserResponse, decodeErrorEnvelope } from "./decoders";
import type { CurrentUserResponse, ErrorEnvelope } from "./types";

const apiBase = "/api/v1";

export class ApiError extends Error {
  readonly envelope: ErrorEnvelope;
  readonly status: number;

  constructor(status: number, envelope: ErrorEnvelope) {
    super(envelope.error.code);
    this.status = status;
    this.envelope = envelope;
  }
}

export function readCsrfCookie(): string | null {
  const entry = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith("mi_csrf="));
  return entry ? decodeURIComponent(entry.slice("mi_csrf=".length)) : null;
}

export async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const method = (init.method ?? "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = readCsrfCookie();
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }
  return fetch(`${apiBase}${path}`, { ...init, headers, credentials: "include" });
}

export async function fetchCurrentUser(): Promise<CurrentUserResponse> {
  const response = await authFetch("/auth/me");
  const payload: unknown = await response.json();
  if (!response.ok) throw new ApiError(response.status, decodeErrorEnvelope(payload));
  return decodeCurrentUserResponse(payload);
}

export async function logoutEverywhere(): Promise<void> {
  const response = await authFetch("/auth/logout", { method: "POST" });
  if (!response.ok) {
    const payload: unknown = await response.json();
    throw new ApiError(response.status, decodeErrorEnvelope(payload));
  }
}
