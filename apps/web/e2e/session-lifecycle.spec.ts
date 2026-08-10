import { expect, test } from "@playwright/test";

test("global logout closes two browser contexts and re-enable requires fresh login", async ({
  browser
}) => {
  let active = true;
  const contexts = await Promise.all([browser.newContext(), browser.newContext()]);
  const pages = await Promise.all(contexts.map(async (context) => context.newPage()));
  const firstPage = pages[0];
  for (const page of pages) {
    await page.route("**/api/v1/auth/me", (route) => {
      if (!active) {
        return route.fulfill({
          status: 401,
          json: {
            error: {
              code: "SESSION_REVOKED",
              recovery: "SIGN_IN_AGAIN",
              message: "Your session ended. Sign in again.",
              correlationId: "e2e-revoked"
            }
          }
        });
      }
      return route.fulfill({
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
      });
    });
    await page.route("**/api/v1/auth/logout", (route) => {
      active = false;
      return route.fulfill({ status: 204 });
    });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Job descriptions" })).toBeVisible();
    await page.goto("/protected");
    await expect(page.getByRole("heading", { name: "Page unavailable" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Return to your home" })).toHaveAttribute(
      "href",
      "/manager/jds"
    );
  }

  await firstPage.evaluate(async () => {
    await fetch("/api/v1/auth/logout", { method: "POST" });
  });
  for (const page of pages) {
    await page.reload();
    await expect(page.getByRole("heading", { name: "Your session ended" })).toBeVisible();
    await page.goBack();
    await expect(page.getByRole("heading", { name: "Your session ended" })).toBeVisible();
  }

  active = true;
  await firstPage.reload();
  await expect(firstPage.getByRole("heading", { name: "Job descriptions" })).toBeVisible();
  await Promise.all(contexts.map(async (context) => context.close()));
});
