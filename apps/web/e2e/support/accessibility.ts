import { expect, type Page } from "@playwright/test";
import axe from "axe-core";

type AxeResult = { violations: { id: string }[] };

export async function expectAccessible(page: Page): Promise<void> {
  await page.addScriptTag({ content: axe.source });
  const results = await page.evaluate(async () => {
    const engine = (window as unknown as { axe: { run: () => Promise<AxeResult> } }).axe;
    return engine.run();
  });
  expect(results.violations).toEqual([]);
}
