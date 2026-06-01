import { expect, test as base, type Locator, type Page } from "@playwright/test";
import type { MockWorkbenchFixture } from "../../src/qa/mock-api";

const consoleAllowlist = [
  "Download the React DevTools",
  'apple-mobile-web-app-capable',
];

export const test = base.extend({
  page: async ({ page }, use) => {
    const errors: string[] = [];
    page.on("console", (message) => {
      const text = message.text();
      if (message.type() === "error" && !consoleAllowlist.some((allowed) => text.includes(allowed))) {
        errors.push(text);
      }
    });
    page.on("pageerror", (error) => {
      errors.push(error.message);
    });
    await use(page);
    expect(errors, "unexpected browser console/page errors").toEqual([]);
  },
});

export { expect } from "@playwright/test";

export function fixture(overrides: MockWorkbenchFixture = {}): MockWorkbenchFixture {
  return {
    ...overrides,
    settings: {
      ...(overrides.settings ?? {}),
      featureSwitches: {
        mcpTools: true,
        ...(overrides.settings?.featureSwitches ?? {}),
      },
    },
  };
}

export async function prepareWorkbench(page: Page, overrides: MockWorkbenchFixture = {}) {
  await page.addInitScript((input) => {
    const qaWindow = window as Window & {
      __TRUSTGRAPH_WORKBENCH_QA__?: unknown;
      __TRUSTGRAPH_WORKBENCH_CLIPBOARD__?: string;
    };
    window.localStorage.clear();
    qaWindow.__TRUSTGRAPH_WORKBENCH_QA__ = {
      enabled: true,
      fixture: input,
      flowId: "default",
    };
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: (text: string) => {
          qaWindow.__TRUSTGRAPH_WORKBENCH_CLIPBOARD__ = text;
          return Promise.resolve();
        },
        readText: () => Promise.resolve(qaWindow.__TRUSTGRAPH_WORKBENCH_CLIPBOARD__ ?? ""),
      },
    });
  }, fixture(overrides));
}

export async function gotoWorkbench(page: Page, path: string, overrides: MockWorkbenchFixture = {}) {
  await prepareWorkbench(page, overrides);
  await page.goto(path);
  await expect(page.locator("body")).not.toContainText("Something went wrong");
}

export async function expectHeading(page: Page, name: string) {
  await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
}

export async function expectCanvasNonBlank(canvas: Locator) {
  await expect(canvas).toBeVisible();
  await expect.poll(() => canvas.evaluate((node) => {
    if (!(node instanceof HTMLCanvasElement)) return false;
    const context = node.getContext("2d");
    if (context === null || node.width === 0 || node.height === 0) return false;
    const pixels = context.getImageData(0, 0, node.width, node.height).data;
    for (let index = 3; index < pixels.length; index += 16) {
      if (pixels[index] !== 0) return true;
    }
    return false;
  }), { timeout: 10_000 }).toBe(true);
}
