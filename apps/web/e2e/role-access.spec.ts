import { expect, test } from "@playwright/test";

test("Candidate, Manager, and Admin navigation remains role scoped", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      json: {
        user: {
          id: "manager-1",
          organizationId: "org-1",
          displayName: "Manager",
          email: "manager@example.test",
          profilePictureUrl: null,
          role: "MANAGER"
        },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    })
  );
  await page.goto("/");
  await expect(page.getByRole("navigation", { name: "Role navigation" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Job descriptions" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Schedule interview" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Job descriptions" })).toBeVisible();
  await expect(page.getByText("Manage users")).toHaveCount(0);
  await expect(page.getByText("No interviews have been allocated yet.")).toHaveCount(0);

  await page.goto("/admin");
  await expect(page.getByRole("alert")).toContainText(
    "This page is not available for your role."
  );
  await expect(page.getByText("Manage users and review application reports.")).toHaveCount(0);

  await page.goto("/unknown-saved-route");
  await expect(page.getByRole("heading", { name: "Page unavailable" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Return to your home" })).toHaveAttribute(
    "href",
    "/manager/jds"
  );
});
