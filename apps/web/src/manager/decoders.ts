import type {
  ManagerCandidate,
  ManagerCandidatePage,
  ManagerInterview,
  ManagerInterviewPage,
  ManagerJobDescription,
  ManagerJobDescriptionPage
} from "./types";

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) throw new Error("Expected object");
  return value as Record<string, unknown>;
}

function string(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) throw new Error(`Expected ${field}`);
  return value;
}

function integer(value: unknown, field: string, minimum: number): number {
  if (!Number.isInteger(value) || (value as number) < minimum) throw new Error(`Expected ${field}`);
  return value as number;
}

export function decodeManagerJobDescription(value: unknown): ManagerJobDescription {
  const input = record(value);
  const sourceType = string(input.sourceType, "sourceType");
  if (sourceType !== "MANUAL" && sourceType !== "UPLOAD") throw new Error("Unknown source type");
  const format = input.sourceFormat;
  if (format !== null && format !== "PDF" && format !== "DOCX" && format !== "TXT") {
    throw new Error("Unknown source format");
  }
  return {
    id: string(input.id, "id"),
    title: string(input.title, "title"),
    sourceType,
    sourceFormat: format,
    createdAt: string(input.createdAt, "createdAt")
  };
}

export function decodeManagerJobDescriptionPage(value: unknown): ManagerJobDescriptionPage {
  const input = record(value);
  if (!Array.isArray(input.items)) throw new Error("Expected items");
  return {
    items: input.items.map(decodeManagerJobDescription),
    page: integer(input.page, "page", 1),
    pageSize: integer(input.pageSize, "pageSize", 1),
    totalItems: integer(input.totalItems, "totalItems", 0),
    totalPages: integer(input.totalPages, "totalPages", 0)
  };
}

function decodeManagerCandidate(value: unknown): ManagerCandidate {
  const input = record(value);
  return {
    id: string(input.id, "id"),
    displayName: string(input.displayName, "displayName"),
    email: string(input.email, "email")
  };
}

function pageMetadata(input: Record<string, unknown>): Omit<ManagerCandidatePage, "items"> {
  return {
    page: integer(input.page, "page", 1),
    pageSize: integer(input.pageSize, "pageSize", 1),
    totalItems: integer(input.totalItems, "totalItems", 0),
    totalPages: integer(input.totalPages, "totalPages", 0)
  };
}

export function decodeManagerCandidatePage(value: unknown): ManagerCandidatePage {
  const input = record(value);
  if (!Array.isArray(input.items)) throw new Error("Expected items");
  return { items: input.items.map(decodeManagerCandidate), ...pageMetadata(input) };
}

function decodeManagerInterview(value: unknown): ManagerInterview {
  const input = record(value);
  const job = record(input.jobDescription);
  if (input.status !== "SCHEDULED") throw new Error("Unknown interview status");
  return {
    id: string(input.id, "id"),
    candidate: decodeManagerCandidate(input.candidate),
    jobDescription: { id: string(job.id, "jobDescription.id"), title: string(job.title, "jobDescription.title") },
    scheduledAt: string(input.scheduledAt, "scheduledAt"),
    status: input.status
  };
}

export function decodeManagerInterviewPage(value: unknown): ManagerInterviewPage {
  const input = record(value);
  if (!Array.isArray(input.items)) throw new Error("Expected items");
  return { items: input.items.map(decodeManagerInterview), ...pageMetadata(input) };
}

export function decodeScheduledInterview(value: unknown): ManagerInterview {
  return decodeManagerInterview(value);
}
