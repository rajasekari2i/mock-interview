import type { CandidateInterview, CandidateInterviewPage } from "./types";

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Expected an object");
  }
  return value as Record<string, unknown>;
}

function string(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) throw new Error(`Expected ${field}`);
  return value;
}

function positiveInteger(value: unknown, field: string): number {
  if (!Number.isInteger(value) || (value as number) < 1) throw new Error(`Expected ${field}`);
  return value as number;
}

function nonnegativeInteger(value: unknown, field: string): number {
  if (!Number.isInteger(value) || (value as number) < 0) throw new Error(`Expected ${field}`);
  return value as number;
}

function decodeInterview(value: unknown): CandidateInterview {
  const input = record(value);
  const jd = record(input.jobDescription);
  const status = string(input.status, "status");
  if (status !== "SCHEDULED") throw new Error("Unknown interview status");
  return {
    id: string(input.id, "id"),
    jobDescription: {
      id: string(jd.id, "jobDescription.id"),
      title: string(jd.title, "jobDescription.title")
    },
    scheduledAt: string(input.scheduledAt, "scheduledAt"),
    status
  };
}

export function decodeCandidateInterviewPage(value: unknown): CandidateInterviewPage {
  const input = record(value);
  if (!Array.isArray(input.items)) throw new Error("Expected items");
  return {
    items: input.items.map(decodeInterview),
    page: positiveInteger(input.page, "page"),
    pageSize: positiveInteger(input.pageSize, "pageSize"),
    totalItems: nonnegativeInteger(input.totalItems, "totalItems"),
    totalPages: nonnegativeInteger(input.totalPages, "totalPages")
  };
}
