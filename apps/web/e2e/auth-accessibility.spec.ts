import { expect, test, type Page } from "@playwright/test";
import axe from "axe-core";

type AxeResult = { violations: { id: string }[] };

async function expectAccessible(page: Page): Promise<void> {
  await page.addScriptTag({ content: axe.source });
  const results = await page.evaluate(async () => {
    const engine = (window as unknown as { axe: { run: () => Promise<AxeResult> } }).axe;
    return engine.run();
  });
  expect(results.violations).toEqual([]);
}

test("login and safe authentication error views meet automated WCAG checks", async ({ page }) => {
  let error = false;
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill(
      error
        ? {
            status: 503,
            json: {
              error: {
                code: "OAUTH_PROVIDER_UNAVAILABLE",
                recovery: "RETRY",
                message: "Google sign-in is temporarily unavailable. Try again.",
                correlationId: "a11y-error"
              }
            }
          }
        : {
            status: 401,
            json: {
              error: {
                code: "AUTHENTICATION_REQUIRED",
                recovery: "SIGN_IN_AGAIN",
                message: "Sign in to continue.",
                correlationId: "a11y-login"
              }
            }
          }
    )
  );
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in to MockInterview" })).toBeFocused();
  await expectAccessible(page);
  error = true;
  await page.reload();
  await expect(page.getByRole("alert")).toBeVisible();
  await expectAccessible(page);
});

test("each role landing and expired-session view has semantics, focus, and no axe violations", async ({
  page
}) => {
  let response: object = {};
  await page.route("**/api/v1/auth/me", (route) => route.fulfill(response));
  for (const [role, heading] of [
    ["CANDIDATE", "Your allocated interviews"],
    ["MANAGER", "Manager workspace"],
    ["ADMIN", "Application administration"]
  ] as const) {
    response = {
      json: {
        user: {
          id: "user-1",
          organizationId: "org-1",
          displayName: role,
          role,
          ...(role === "CANDIDATE" ? { candidateProfileId: "profile-1" } : {})
        },
        session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
      }
    };
    await page.goto("/");
    await expect(page.getByRole("heading", { name: heading })).toBeFocused();
    await expectAccessible(page);
  }
  response = {
    status: 401,
    json: {
      error: {
        code: "SESSION_EXPIRED",
        recovery: "SIGN_IN_AGAIN",
        message: "Your session ended. Sign in again.",
        correlationId: "a11y-expired"
      }
    }
  };
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Your session ended" })).toBeFocused();
  await expectAccessible(page);
});

test("mapping denial, revoked session, and fresh sign-in recovery remain accessible", async ({
  page
}) => {
  await page.goto(
    "/auth/error?code=ACCESS_NOT_PROVISIONED&correlation_id=a11y-unmapped"
  );
  await expect(page.getByRole("heading", { name: "Access unavailable" })).toBeFocused();
  await expect(page.getByRole("alert")).toContainText("Contact your administrator");
  await expectAccessible(page);

  let fresh = false;
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill(
      fresh
        ? {
            json: {
              user: {
                id: "candidate-1",
                organizationId: "target-org",
                displayName: "Candidate",
                role: "CANDIDATE",
                candidateProfileId: "profile-1"
              },
              session: { absoluteExpiresAt: "later", idleExpiresAt: "soon" }
            }
          }
        : {
            status: 401,
            json: {
              error: {
                code: "SESSION_REVOKED",
                recovery: "SIGN_IN_AGAIN",
                message: "Your session ended. Sign in again.",
                correlationId: "a11y-reassigned"
              }
            }
          }
    )
  );
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Your session ended" })).toBeFocused();
  await expectAccessible(page);
  fresh = true;
  await page.reload();
  await expect(page.getByRole("heading", { name: "Your allocated interviews" })).toBeFocused();
  await expectAccessible(page);
});
