import { expect, test } from "@playwright/test";

import { expectAccessible } from "./support/accessibility";

const pageEnvelope = { items: [], page: 1, pageSize: 25, totalItems: 0, totalPages: 0 };

for (const role of ["CANDIDATE", "MANAGER", "ADMIN"] as const) {
  test(`${role} empty home and profile disclosure pass automated accessibility checks`, async ({ page }) => {
    await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: {
      user: { id: "user-1", organizationId: "org-1", displayName: role, email: `${role.toLowerCase()}@example.test`, profilePictureUrl: null, role, ...(role === "CANDIDATE" ? { candidateProfileId: "profile-1" } : {}) },
      session: { absoluteExpiresAt: "2099", idleExpiresAt: "2099" }
    } }));
    await page.route("**/api/v1/candidate/**", (route) => route.fulfill({ json: pageEnvelope }));
    await page.route("**/api/v1/manager/**", (route) => route.fulfill({ json: pageEnvelope }));
    await page.route("**/api/v1/admin/**", (route) => route.fulfill({ json: pageEnvelope }));
    await page.goto(`/${role.toLowerCase()}`);
    await expect(page.locator("h1")).toBeFocused();
    await expectAccessible(page);
    await page.getByRole("button", { name: "Open profile menu" }).click();
    await expectAccessible(page);
    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Open profile menu" })).toBeFocused();
  });
}

test("Manager mobile form error remains operable without page-level horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: {
    user: { id: "manager-1", organizationId: "org-1", displayName: "Manager", email: "manager@example.test", profilePictureUrl: null, role: "MANAGER" },
    session: { absoluteExpiresAt: "2099", idleExpiresAt: "2099" }
  } }));
  await page.route("**/api/v1/manager/**", (route) => route.fulfill({ json: pageEnvelope }));
  await page.goto("/manager/jds/new");
  await page.getByRole("button", { name: "Upload document" }).click();
  await page.getByLabel("JD title").fill("Invalid upload");
  await page.getByLabel("JD document").setInputFiles({ name: "unsafe.exe", mimeType: "application/octet-stream", buffer: Buffer.from("unsafe") });
  await page.getByRole("button", { name: "Upload job description" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expectAccessible(page);
  const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width);
});

test("Admin detail dialog has no axe violations and restores keyboard focus on Escape", async ({ page }) => {
  const user = { id: "user-2", organizationId: "org-1", displayName: "Candidate", email: "candidate@example.test", profilePictureUrl: null, role: "CANDIDATE", status: "ACTIVE", candidateProfileId: "profile-1" };
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: {
    user: { id: "admin-1", organizationId: "org-1", displayName: "Admin", email: "admin@example.test", profilePictureUrl: null, role: "ADMIN" },
    session: { absoluteExpiresAt: "2099", idleExpiresAt: "2099" }
  } }));
  await page.route("**/api/v1/admin/job-descriptions**", (route) => route.fulfill({ json: pageEnvelope }));
  await page.route("**/api/v1/admin/users**", (route) => route.fulfill({ json: { ...pageEnvelope, items: [user], totalItems: 1, totalPages: 1 } }));
  await page.route("**/api/v1/admin/users/user-2", (route) => route.fulfill({ json: user }));
  await page.goto("/admin");
  const opener = page.getByRole("button", { name: "View details for Candidate" });
  await opener.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expectAccessible(page);
  await page.keyboard.press("Escape");
  await expect(opener).toBeFocused();
});
