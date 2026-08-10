import type { CurrentUser, Role } from "../auth/types";

export type TestRole = Role;

export interface TestCurrentUser {
  id: string;
  organizationId: string;
  displayName: string;
  email: string;
  profilePictureUrl: string | null;
  role: TestRole;
  candidateProfileId?: string;
}

export interface TestPage<T> {
  items: T[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

export function currentUser(role: TestRole = "CANDIDATE"): CurrentUser {
  return {
    id: "00000000-0000-0000-0000-000000000001",
    organizationId: "00000000-0000-0000-0000-000000000010",
    displayName: `Test ${role.toLowerCase()}`,
    email: `${role.toLowerCase()}@example.test`,
    profilePictureUrl: null,
    role,
    ...(role === "CANDIDATE"
      ? { candidateProfileId: "00000000-0000-0000-0000-000000000011" }
      : {})
  } as CurrentUser;
}

export function page<T>(items: T[]): TestPage<T> {
  return {
    items,
    page: 1,
    pageSize: 25,
    totalItems: items.length,
    totalPages: items.length === 0 ? 0 : 1
  };
}

export function jobDescription() {
  return {
    id: "00000000-0000-0000-0000-000000000020",
    title: "Platform Engineer",
    sourceType: "MANUAL" as const,
    sourceFormat: null,
    createdAt: "2026-08-10T09:00:00Z"
  };
}

export function candidateSelection() {
  return {
    id: "00000000-0000-0000-0000-000000000030",
    displayName: "Test candidate",
    email: "candidate@example.test"
  };
}

export function scheduledInterview() {
  return {
    id: "00000000-0000-0000-0000-000000000040",
    candidate: candidateSelection(),
    jobDescription: {
      id: jobDescription().id,
      title: jobDescription().title
    },
    scheduledAt: "2026-08-11T09:00:00Z",
    status: "SCHEDULED" as const
  };
}
