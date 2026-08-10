import { chmod, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { performance } from "node:perf_hooks";

import { expect, test, type BrowserContext } from "@playwright/test";

type Role = "CANDIDATE" | "MANAGER" | "ADMIN";
type SessionState = { token: string; csrfToken: string; homePath: string };
type SeedState = {
  cookieName: string;
  csrfCookieName: string;
  sessions: Record<Role, SessionState>;
};
type Sample = { role: Role; milliseconds: number; outcome: "success" | "timeout" };

const roles: Role[] = ["CANDIDATE", "MANAGER", "ADMIN"];
const expectedContent: Record<Role, string> = {
  CANDIDATE: "Performance Job Description 0000",
  MANAGER: "Your job descriptions",
  ADMIN: "Application users"
};

function assertState(value: unknown): asserts value is SeedState {
  if (typeof value !== "object" || value === null || !("sessions" in value)) {
    throw new Error("Performance session state is invalid");
  }
}

function percentile(values: number[], fraction: number): number {
  const ordered = [...values].sort((left, right) => left - right);
  return ordered[Math.min(ordered.length - 1, Math.floor((ordered.length - 1) * fraction))] ?? 0;
}

async function configureSession(
  context: BrowserContext,
  origin: string,
  state: SeedState,
  role: Role
): Promise<void> {
  const session = state.sessions[role];
  await context.addCookies([
    { name: state.cookieName, value: session.token, url: origin, httpOnly: true, sameSite: "Lax" },
    { name: state.csrfCookieName, value: session.csrfToken, url: origin, sameSite: "Lax" }
  ]);
}

test("at least 95 of 100 role-home views render within two seconds under ten contexts", async ({ browser, baseURL }) => {
  const stateDir = process.env.PERFORMANCE_STATE_DIR;
  if (stateDir === undefined || baseURL === undefined) throw new Error("Performance environment is incomplete");
  const parsed: unknown = JSON.parse(await readFile(join(stateDir, "sessions.json"), "utf8"));
  assertState(parsed);
  const samples: Sample[] = [];

  await Promise.all(Array.from({ length: 10 }, async (_, contextIndex) => {
    const role = roles[contextIndex % roles.length];
    const context = await browser.newContext();
    await configureSession(context, baseURL, parsed, role);
    const page = await context.newPage();
    for (let iteration = 0; iteration < 10; iteration += 1) {
      const started = performance.now();
      try {
        if (iteration === 0 || iteration % 2 === 0) {
          await page.goto(parsed.sessions[role].homePath, { waitUntil: "domcontentloaded" });
        } else {
          await page.reload({ waitUntil: "domcontentloaded" });
        }
        await page.getByRole("button", { name: "Open profile menu" }).waitFor({ timeout: 2_000 });
        await page.getByText(expectedContent[role], { exact: false }).first().waitFor({ timeout: 2_000 });
        samples.push({ role, milliseconds: performance.now() - started, outcome: "success" });
      } catch {
        samples.push({ role, milliseconds: performance.now() - started, outcome: "timeout" });
      }
    }
    await context.close();
  }));

  const successful = samples.filter((sample) => sample.outcome === "success");
  const withinThreshold = successful.filter((sample) => sample.milliseconds <= 2_000).length;
  const durations = samples.map((sample) => sample.milliseconds);
  const report = {
    schemaVersion: 1,
    recordedAt: new Date().toISOString(),
    configuration: { samples: 100, browserContexts: 10, thresholdMilliseconds: 2_000 },
    results: {
      successes: successful.length,
      failures: samples.length - successful.length,
      withinThreshold,
      p50Milliseconds: percentile(durations, 0.5),
      p95Milliseconds: percentile(durations, 0.95),
      maxMilliseconds: Math.max(...durations),
      byRole: Object.fromEntries(roles.map((role) => [role, samples.filter((sample) => sample.role === role).length]))
    }
  };
  const outputPath = join(stateDir, "browser-performance.json");
  await writeFile(outputPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  await chmod(outputPath, 0o600);
  expect(samples).toHaveLength(100);
  expect(withinThreshold).toBeGreaterThanOrEqual(95);
});
