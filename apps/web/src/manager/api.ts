import { authFetch } from "../auth/api";
import {
  decodeManagerCandidatePage,
  decodeManagerInterviewPage,
  decodeManagerJobDescription,
  decodeManagerJobDescriptionPage,
  decodeScheduledInterview
} from "./decoders";
import type {
  ManagerCandidatePage,
  ManagerInterview,
  ManagerInterviewPage,
  ManagerJobDescription,
  ManagerJobDescriptionPage
} from "./types";

async function requireJson(response: Response): Promise<unknown> {
  if (!response.ok) throw new Error(`Request failed:${String(response.status)}`);
  return response.json();
}

export async function fetchManagerJobDescriptions(): Promise<ManagerJobDescriptionPage> {
  const response = await authFetch("/manager/job-descriptions?page=1&pageSize=25");
  return decodeManagerJobDescriptionPage(await requireJson(response));
}

export async function createManualJobDescription(
  title: string,
  content: string
): Promise<ManagerJobDescription> {
  const response = await authFetch("/manager/job-descriptions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, content })
  });
  return decodeManagerJobDescription(await requireJson(response));
}

export async function uploadJobDescription(
  title: string,
  document: File
): Promise<ManagerJobDescription> {
  const body = new FormData();
  body.set("title", title);
  body.set("document", document);
  const response = await authFetch("/manager/job-descriptions/upload", {
    method: "POST",
    body
  });
  return decodeManagerJobDescription(await requireJson(response));
}

export async function fetchManagerCandidates(): Promise<ManagerCandidatePage> {
  const response = await authFetch("/manager/candidates?page=1&pageSize=100");
  return decodeManagerCandidatePage(await requireJson(response));
}

export async function fetchManagerInterviews(): Promise<ManagerInterviewPage> {
  const response = await authFetch("/manager/interviews?page=1&pageSize=25");
  return decodeManagerInterviewPage(await requireJson(response));
}

export async function scheduleInterview(
  candidateId: string,
  jobDescriptionId: string,
  scheduledAt: string,
  idempotencyKey: string
): Promise<ManagerInterview> {
  const response = await authFetch("/manager/interviews", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({ candidateId, jobDescriptionId, scheduledAt })
  });
  return decodeScheduledInterview(await requireJson(response));
}
