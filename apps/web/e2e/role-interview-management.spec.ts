import { expect, test, type Page, type Route } from "@playwright/test";

const orgId = "00000000-0000-0000-0000-000000000010";
const userId = "00000000-0000-0000-0000-000000000001";
const candidateId = "00000000-0000-0000-0000-000000000030";
const jdId = "00000000-0000-0000-0000-000000000020";

function pageOf(items: object[]) {
  return { items, page: 1, pageSize: 25, totalItems: items.length, totalPages: items.length ? 1 : 0 };
}

async function authenticate(page: Page, role: "CANDIDATE" | "MANAGER" | "ADMIN") {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: {
    user: {
      id: userId,
      organizationId: orgId,
      displayName: `${role[0]}${role.slice(1).toLowerCase()} Person`,
      email: `${role.toLowerCase()}@example.test`,
      profilePictureUrl: null,
      role,
      ...(role === "CANDIDATE" ? { candidateProfileId: candidateId } : {})
    },
    session: { absoluteExpiresAt: "2099-01-01T00:00:00Z", idleExpiresAt: "2099-01-01T00:00:00Z" }
  }}));
}

test("Candidate sees only the self-scoped allocation and can use profile and logout by keyboard", async ({ page }) => {
  await authenticate(page, "CANDIDATE");
  await page.route("**/api/v1/candidate/interviews**", (route) => route.fulfill({ json: pageOf([{
    id: "00000000-0000-0000-0000-000000000040",
    jobDescription: { id: jdId, title: "Platform Engineer" },
    scheduledAt: "2099-08-11T09:00:00Z",
    status: "SCHEDULED"
  }]) }));
  await page.route("**/api/v1/auth/logout", (route) => route.fulfill({ status: 204 }));

  await page.goto("/candidate");
  await expect(page.getByText("Platform Engineer")).toBeVisible();
  await expect(page.getByText("Other candidate interview")).toHaveCount(0);
  await page.getByRole("button", { name: "Open profile menu" }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("link", { name: "Profile" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Your profile" })).toBeFocused();
  await expect(page.getByText("candidate@example.test")).toBeVisible();
  await page.getByRole("button", { name: "Open profile menu" }).click();
  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page.getByRole("heading", { name: "Sign in to MockInterview" })).toBeFocused();
});

test("Manager creates a JD and schedules it for an active candidate", async ({ page }) => {
  await authenticate(page, "MANAGER");
  const jd = { id: jdId, title: "Platform Engineer", sourceType: "MANUAL", sourceFormat: null, createdAt: "2026-08-10T09:00:00Z" };
  const uploadedJd = { ...jd, id: "00000000-0000-0000-0000-000000000021", sourceType: "UPLOAD", sourceFormat: "TXT", title: "Uploaded Engineer" };
  const candidate = { id: candidateId, displayName: "Candidate Person", email: "candidate@example.test" };
  const jobDescriptions: object[] = [];
  await page.route("**/api/v1/manager/**", async (route: Route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/candidates")) return route.fulfill({ json: pageOf([candidate]) });
    if (path.endsWith("/interviews") && request.method() === "POST") {
      return route.fulfill({ status: 201, json: { id: "00000000-0000-0000-0000-000000000040", candidate, jobDescription: { id: jdId, title: "Platform Engineer" }, scheduledAt: "2099-08-11T09:00:00.000Z", status: "SCHEDULED" } });
    }
    if (path.endsWith("/interviews")) return route.fulfill({ json: pageOf([]) });
    if (path.endsWith("/job-descriptions/upload")) {
      jobDescriptions.unshift(uploadedJd);
      return route.fulfill({ status: 201, json: uploadedJd });
    }
    if (path.endsWith("/job-descriptions") && request.method() === "POST") {
      jobDescriptions.unshift(jd);
      return route.fulfill({ status: 201, json: jd });
    }
    if (path.endsWith("/job-descriptions")) return route.fulfill({ json: pageOf(jobDescriptions) });
    return route.fulfill({ json: pageOf([]) });
  });

  await page.goto("/manager/jds");
  await page.getByRole("link", { name: "Create job description" }).click();
  await page.getByLabel("JD title").fill("Platform Engineer");
  await page.getByLabel("Job description content").fill("Build reliable platforms.");
  await page.getByRole("button", { name: "Create job description" }).click();
  await expect(page.getByRole("status")).toContainText("Job description created");
  await page.getByRole("button", { name: "Upload document" }).click();
  await page.getByLabel("JD title").fill("Uploaded Engineer");
  await page.getByLabel("JD document").setInputFiles({ name: "role.txt", mimeType: "text/plain", buffer: Buffer.from("Role text") });
  await page.getByRole("button", { name: "Upload job description" }).click();
  await page.getByRole("link", { name: "Back to job descriptions" }).click();
  await expect(page.getByRole("cell", { name: "Uploaded Engineer" })).toBeVisible();
  await page.getByRole("link", { name: "Schedule interview" }).click();
  await page.getByLabel("Candidate").selectOption(candidateId);
  await page.getByRole("combobox", { name: /Job description/ }).selectOption(jdId);
  await page.getByLabel("Interview date").fill("2099-08-11");
  await page.getByLabel("Interview time").fill("09:00");
  await page.getByRole("button", { name: "Schedule interview" }).click();
  await expect(page.getByText("Interview scheduled.")).toBeVisible();
  await expect(page.getByRole("cell", { name: "Candidate Person", exact: true })).toBeVisible();
});

test("Admin pages independently and changes a user's role in the detail dialog", async ({ page }) => {
  await authenticate(page, "ADMIN");
  let role = "CANDIDATE";
  const adminCreatedJd = { id: "00000000-0000-0000-0000-000000000022", title: "Admin-created Engineer", sourceType: "MANUAL", sourceFormat: null, createdAt: "2026-08-10T09:30:00Z" };
  const user = () => ({ id: candidateId, organizationId: orgId, displayName: "Candidate Person", email: "candidate@example.test", role, status: "ACTIVE", profilePictureUrl: null, candidateProfileId: candidateId });
  await page.route("**/api/v1/manager/job-descriptions", (route) => route.fulfill({ status: 201, json: adminCreatedJd }));
  await page.route("**/api/v1/admin/**", (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/job-descriptions")) return route.fulfill({ json: pageOf([{ id: jdId, organizationId: orgId, title: "Platform Engineer", sourceType: "MANUAL", sourceFormat: null, createdAt: "2026-08-10T09:00:00Z", createdBy: { id: userId, displayName: "Manager Person" } }]) });
    if (path.endsWith("/role")) {
      const payload: unknown = JSON.parse(request.postData() ?? "{}");
      if (typeof payload === "object" && payload !== null && "role" in payload && typeof payload.role === "string") role = payload.role;
      return route.fulfill({ json: user() });
    }
    if (path.endsWith(`/users/${candidateId}`)) return route.fulfill({ json: user() });
    return route.fulfill({ json: pageOf([user()]) });
  });

  await page.goto("/admin?usersPage=1");
  await expect(page.getByRole("heading", { name: "Job descriptions" })).toHaveCount(0);
  await page.getByRole("link", { name: "Job descriptions" }).click();
  await expect(page.getByText("Platform Engineer")).toBeVisible();
  await page.getByRole("link", { name: "Create job description" }).click();
  await page.getByLabel("JD title").fill("Admin-created Engineer");
  await page.getByLabel("Job description content").fill("Admin-created role details.");
  await page.getByRole("button", { name: "Create job description" }).click();
  await expect(page.getByRole("status")).toContainText("Job description created");
  await page.getByRole("link", { name: "Users" }).click();
  await page.getByRole("button", { name: "View details for Candidate Person" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("dialog").getByRole("combobox").selectOption("MANAGER");
  await page.getByRole("button", { name: "Save role" }).click();
  await expect(page.getByRole("status")).toHaveText("Role updated.");
  await page.getByRole("button", { name: "Close" }).click();
  await expect(page.getByRole("cell", { name: "MANAGER", exact: true })).toBeVisible();
});
