import type { Role } from "../auth/types";

export type UserStatus = "ACTIVE" | "DISABLED";

export interface AdminUser {
  id: string;
  organizationId: string;
  displayName: string;
  email: string;
  role: Role;
  status: UserStatus;
  profilePictureUrl?: string | null;
  candidateProfileId?: string | null;
}

export interface Page<T> {
  items: T[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

export interface AdminJobDescription {
  id: string;
  organizationId: string;
  title: string;
  sourceType: "MANUAL" | "UPLOAD";
  sourceFormat: "PDF" | "DOCX" | "TXT" | null;
  createdAt: string;
  createdBy: { id: string; displayName: string };
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  status: "ACTIVE";
  createdAt: string;
  updatedAt: string;
}

export interface OrganizationList {
  items: Organization[];
}
