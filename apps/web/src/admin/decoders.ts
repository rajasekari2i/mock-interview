import type { AdminJobDescription, AdminUser, Organization, OrganizationList, Page, UserStatus } from "./types";
import type { Role } from "../auth/types";

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) throw new Error("Expected object");
  return value as Record<string, unknown>;
}

function string(value: unknown, field: string): string {
  if (typeof value !== "string" || !value) throw new Error(`Expected ${field}`);
  return value;
}

function role(value: unknown): Role {
  if (value !== "CANDIDATE" && value !== "MANAGER" && value !== "ADMIN") throw new Error("Expected role");
  return value;
}

function status(value: unknown): UserStatus {
  if (value !== "ACTIVE" && value !== "DISABLED") throw new Error("Expected status");
  return value;
}

function metadata<T>(input: Record<string, unknown>, items: T[]): Page<T> {
  for (const key of ["page", "pageSize", "totalItems", "totalPages"] as const) {
    if (!Number.isInteger(input[key]) || (input[key] as number) < (key === "page" ? 1 : 0)) throw new Error(`Expected ${key}`);
  }
  return { items, page: input.page as number, pageSize: input.pageSize as number, totalItems: input.totalItems as number, totalPages: input.totalPages as number };
}

export function decodeAdminUser(value: unknown): AdminUser {
  const input = record(value);
  const optional = (field: "profilePictureUrl" | "candidateProfileId"): string | null | undefined => {
    const value = input[field];
    if (value === undefined || value === null) return value;
    return string(value, field);
  };
  return {
    id: string(input.id, "id"), organizationId: string(input.organizationId, "organizationId"),
    displayName: string(input.displayName, "displayName"), email: string(input.email, "email"),
    role: role(input.role), status: status(input.status),
    ...(input.profilePictureUrl !== undefined ? { profilePictureUrl: optional("profilePictureUrl") } : {}),
    ...(input.candidateProfileId !== undefined ? { candidateProfileId: optional("candidateProfileId") } : {})
  };
}

export function decodeAdminUserPage(value: unknown): Page<AdminUser> {
  const input = record(value);
  if (!Array.isArray(input.items)) throw new Error("Expected items");
  return metadata(input, input.items.map(decodeAdminUser));
}

function decodeAdminJd(value: unknown): AdminJobDescription {
  const input = record(value);
  const creator = record(input.createdBy);
  const sourceType = input.sourceType;
  const sourceFormat = input.sourceFormat;
  if (sourceType !== "MANUAL" && sourceType !== "UPLOAD") throw new Error("Expected sourceType");
  if (sourceFormat !== null && sourceFormat !== "PDF" && sourceFormat !== "DOCX" && sourceFormat !== "TXT") throw new Error("Expected sourceFormat");
  return {
    id: string(input.id, "id"), organizationId: string(input.organizationId, "organizationId"),
    title: string(input.title, "title"), sourceType, sourceFormat,
    createdAt: string(input.createdAt, "createdAt"),
    createdBy: { id: string(creator.id, "createdBy.id"), displayName: string(creator.displayName, "createdBy.displayName") }
  };
}

export function decodeAdminJdPage(value: unknown): Page<AdminJobDescription> {
  const input = record(value);
  if (!Array.isArray(input.items)) throw new Error("Expected items");
  return metadata(input, input.items.map(decodeAdminJd));
}

export function decodeOrganization(value: unknown): Organization {
  const input = record(value);
  if (input.status !== "ACTIVE") throw new Error("Expected organization status");
  return {
    id: string(input.id, "id"),
    name: string(input.name, "name"),
    slug: string(input.slug, "slug"),
    status: input.status,
    createdAt: string(input.createdAt, "createdAt"),
    updatedAt: string(input.updatedAt, "updatedAt")
  };
}

export function decodeOrganizationList(value: unknown): OrganizationList {
  const input = record(value);
  if (!Array.isArray(input.items)) throw new Error("Expected items");
  return { items: input.items.map(decodeOrganization) };
}
