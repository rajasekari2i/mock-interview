import { expect, test } from "@playwright/test";

test("Candidate, Manager, and Admin navigation remains role scoped", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      json: {
        user: {
          id: "manager-1",
          organizationId: "org-1",
          displayName: "Manager",
          role: "MANAGER"
        },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    })
  );
  await page.goto("/");
  await expect(page.getByRole("navigation", { name: "Role navigation" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Candidate allocations" })).toBeVisible();
  await expect(page.getByText("Upload job descriptions")).toBeVisible();
  await expect(page.getByText("Manage users")).toHaveCount(0);
  await expect(page.getByText("No interviews have been allocated yet.")).toHaveCount(0);
});
