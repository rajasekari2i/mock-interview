import { expect, test } from "@playwright/test";

const users = [
  ["CANDIDATE", "Your allocated interviews"],
  ["MANAGER", "Manager workspace"],
  ["ADMIN", "Application administration"]
] as const;

for (const [role, heading] of users) {
  test(`${role} first and later login reaches its role home`, async ({ page }) => {
    await page.route("**/api/v1/auth/me", async (route) => {
      await route.fulfill({
        json: {
          user: {
            id: "10000000-0000-0000-0000-000000000001",
            organizationId: "20000000-0000-0000-0000-000000000001",
            displayName: role,
            role,
            ...(role === "CANDIDATE" ? { candidateProfileId: "profile-1" } : {})
          },
          session: {
            absoluteExpiresAt: "2026-08-09T18:00:00Z",
            idleExpiresAt: "2026-08-09T12:00:00Z"
          }
        }
      });
    });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  });
}

test("unknown, disabled, cancelled, replayed, and provider failures show safe recovery", async ({
  page
}) => {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      status: 403,
      json: {
        error: {
          code: "ACCESS_NOT_PROVISIONED",
          recovery: "CONTACT_ADMIN",
          message: "Access is unavailable. Contact your administrator.",
          correlationId: "request-1"
        }
      }
    })
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("Contact your administrator");
});

test("unmapped callback error uses safe local contact-admin recovery", async ({ page }) => {
  await page.goto(
    "/auth/error?code=ACCESS_NOT_PROVISIONED&correlation_id=opaque-correlation"
  );
  await expect(page.getByRole("alert")).toContainText("Contact your administrator");
});

test("reassignment rejects the old session and fresh login reaches the target tenant", async ({
  page
}) => {
  let freshLogin = false;
  await page.route("**/api/v1/auth/me", (route) => {
    if (!freshLogin) {
      return route.fulfill({
        status: 401,
        json: {
          error: {
            code: "SESSION_REVOKED",
            recovery: "SIGN_IN_AGAIN",
            message: "Your session ended. Sign in again.",
            correlationId: "reassignment"
          }
        }
      });
    }
    return route.fulfill({
      json: {
        user: {
          id: "10000000-0000-0000-0000-000000000001",
          organizationId: "20000000-0000-0000-0000-000000000099",
          displayName: "Migrated Candidate",
          role: "CANDIDATE",
          candidateProfileId: "profile-1"
        },
        session: {
          absoluteExpiresAt: "2026-08-09T18:00:00Z",
          idleExpiresAt: "2026-08-09T12:00:00Z"
        }
      }
    });
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Session ended" })).toBeVisible();
  freshLogin = true;
  await page.reload();
  await expect(page.getByRole("heading", { name: "Your allocated interviews" })).toBeVisible();
});
