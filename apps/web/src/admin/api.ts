import { authFetch } from "../auth/api";
import type { Role } from "../auth/types";
import { decodeAdminJdPage, decodeAdminUser, decodeAdminUserPage, decodeOrganization, decodeOrganizationList } from "./decoders";
import type { AdminJobDescription, AdminUser, Organization, OrganizationList, Page } from "./types";

async function json(response: Response): Promise<unknown> {
  if (!response.ok) throw new Error(`Request failed:${String(response.status)}`);
  return response.json();
}

export async function fetchAdminUsers(page: number): Promise<Page<AdminUser>> {
  return decodeAdminUserPage(await json(await authFetch(`/admin/users?page=${String(page)}&pageSize=25`)));
}

export async function fetchAdminJds(page: number): Promise<Page<AdminJobDescription>> {
  return decodeAdminJdPage(await json(await authFetch(`/admin/job-descriptions?page=${String(page)}&pageSize=25`)));
}

export async function fetchAdminUser(id: string): Promise<AdminUser> {
  return decodeAdminUser(await json(await authFetch(`/admin/users/${encodeURIComponent(id)}`)));
}

export async function saveAdminUserRole(id: string, role: Role): Promise<AdminUser> {
  return decodeAdminUser(await json(await authFetch(`/admin/users/${encodeURIComponent(id)}/role`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role })
  })));
}

export async function fetchAdminOrganizations(): Promise<OrganizationList> {
  return decodeOrganizationList(await json(await authFetch("/admin/organizations")));
}

export async function createAdminOrganization(name: string, slug: string): Promise<Organization> {
  return decodeOrganization(await json(await authFetch("/admin/organizations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, slug })
  })));
}
