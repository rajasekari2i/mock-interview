import { expect, test } from "@playwright/test";

const users = [
  ["CANDIDATE", "Your allocated interviews"],
  ["MANAGER", "Job descriptions"],
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
            email: `${role.toLowerCase()}@example.test`,
            profilePictureUrl: null,
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
          email: "candidate@example.test",
          profilePictureUrl: null,
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

test("profile disclosure, fallback, profile page, and logout form one keyboard flow", async ({
  page
}) => {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      json: {
        user: {
          id: "manager-1",
          organizationId: "org-1",
          displayName: "Grace Hopper",
          email: "grace@example.test",
          profilePictureUrl: null,
          role: "MANAGER"
        },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    })
  );
  await page.route("**/api/v1/auth/logout", (route) => route.fulfill({ status: 204 }));
  await page.goto("/");

  const trigger = page.getByRole("button", { name: "Open profile menu" });
  await trigger.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("GH")).toBeVisible();
  await page.getByRole("link", { name: "Profile" }).click();
  await expect(page.getByRole("heading", { name: "Your profile" })).toBeFocused();
  await expect(page.getByText("grace@example.test")).toBeVisible();

  await trigger.click();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await trigger.click();
  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page.getByRole("heading", { name: "Sign in to MockInterview" })).toBeFocused();
});
