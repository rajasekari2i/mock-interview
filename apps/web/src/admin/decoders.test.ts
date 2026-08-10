import { describe, expect, it } from "vitest";

import { decodeAdminJdPage, decodeAdminUser, decodeAdminUserPage, decodeOrganization, decodeOrganizationList } from "./decoders";

const user = {
  id: "user-1", organizationId: "org-1", displayName: "Ada", email: "ada@example.test",
  role: "MANAGER", status: "ACTIVE", profilePictureUrl: null, candidateProfileId: null
};
const metadata = { page: 1, pageSize: 25, totalItems: 1, totalPages: 1 };

describe("Admin decoders", () => {
  it("decodes user/detail and JD pages and rejects malformed projections", () => {
    expect(decodeAdminUser(user)).toEqual(user);
    expect(decodeAdminUser({ ...user, role: "CANDIDATE", profilePictureUrl: "https://example.test/p.png", candidateProfileId: "profile-1" }).role).toBe("CANDIDATE");
    expect(decodeAdminUser({ ...user, role: "ADMIN" }).role).toBe("ADMIN");
    expect(decodeAdminUserPage({ items: [user], ...metadata }).items[0]?.displayName).toBe("Ada");
    const jd = {
      id: "jd-1", organizationId: "org-1", title: "Engineer", sourceType: "UPLOAD",
      sourceFormat: "PDF", createdAt: "2026-08-10T09:00:00Z",
      createdBy: { id: "user-1", displayName: "Ada" }
    };
    expect(decodeAdminJdPage({ items: [jd], ...metadata }).items[0]).toEqual(jd);
    for (const value of [null, { ...user, role: "OWNER" }, { ...user, status: "SECRET" }]) {
      expect(() => decodeAdminUser(value)).toThrow();
    }
    expect(() => decodeAdminUserPage({ items: {}, ...metadata })).toThrow();
    expect(() => decodeAdminUser({ ...user, email: 1 })).toThrow();
    expect(() => decodeAdminUser({ ...user, email: "" })).toThrow();
    expect(() => decodeAdminUser([])).toThrow();
    expect(() => decodeAdminUserPage({ items: [], ...metadata, page: 0 })).toThrow();
    expect(() => decodeAdminUserPage({ items: [], ...metadata, totalItems: 0.5 })).toThrow();
    expect(() => decodeAdminJdPage({ items: [{ ...jd, createdBy: null }], ...metadata })).toThrow();
    expect(() => decodeAdminJdPage({ items: {}, ...metadata })).toThrow();
    expect(() => decodeAdminJdPage({ items: [{ ...jd, sourceType: "SECRET" }], ...metadata })).toThrow();
    expect(() => decodeAdminJdPage({ items: [{ ...jd, sourceFormat: "EXE" }], ...metadata })).toThrow();
    for (const sourceFormat of [null, "DOCX", "TXT"] as const) {
      expect(decodeAdminJdPage({ items: [{ ...jd, sourceFormat }], ...metadata }).items[0]?.sourceFormat).toBe(sourceFormat);
    }
  });

  it("decodes organization responses and rejects malformed values", () => {
    const organization = {
      id: "org-1", name: "Ideas2IT", slug: "ideas2it", status: "ACTIVE",
      createdAt: "2026-08-10T09:00:00Z", updatedAt: "2026-08-10T09:00:00Z"
    };
    expect(decodeOrganization(organization)).toEqual(organization);
    expect(decodeOrganizationList({ items: [organization] }).items).toEqual([organization]);
    expect(() => decodeOrganization({ ...organization, status: "DISABLED" })).toThrow();
    expect(() => decodeOrganization({ ...organization, name: "" })).toThrow();
    expect(() => decodeOrganizationList({ items: null })).toThrow();
  });
});
