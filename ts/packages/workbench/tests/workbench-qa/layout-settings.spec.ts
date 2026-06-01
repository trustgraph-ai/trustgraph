import { expect, expectHeading, gotoWorkbench, test } from "./fixtures";

const routes = [
  ["/chat", "Chat"],
  ["/library", "Library"],
  ["/graph", "Graph"],
  ["/prompts", "Prompts"],
  ["/token-cost", "Token Cost"],
  ["/knowledge-cores", "Knowledge Cores"],
  ["/flows", "Flows"],
  ["/mcp-tools", "MCP Tools"],
  ["/settings", "Settings"],
] as const;

for (const [route, heading] of routes) {
  test(`loads ${route}`, async ({ page }) => {
    await gotoWorkbench(page, route);
    await expectHeading(page, heading);
    await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();
  });
}

test("settings persist view state and drive feature switches", async ({ page }) => {
  await gotoWorkbench(page, "/settings");
  await expectHeading(page, "Settings");

  const apiKey = page.getByPlaceholder("Optional gateway bearer token");
  await apiKey.fill("qa-secret");
  await expect(apiKey).toHaveAttribute("type", "password");
  await page.getByLabel("Show API key").click();
  await expect(apiKey).toHaveAttribute("type", "text");
  await page.getByLabel("Hide API key").click();
  await expect(apiKey).toHaveAttribute("type", "password");

  await page.getByText("Theme").click();
  await expect.poll(() => page.evaluate(() => document.body.classList.contains("light"))).toBe(true);

  await page.getByLabel("Create collection").click();
  const collectionDialog = page.getByRole("dialog", { name: "Create Collection" });
  await expect(collectionDialog).toBeVisible();
  await collectionDialog.getByRole("textbox", { name: "Collection ID" }).fill("qa-created");
  await collectionDialog.getByRole("textbox", { name: "Display Name" }).fill("QA Created");
  await collectionDialog.getByRole("button", { name: "Create", exact: true }).click();
  await expect(page.getByRole("option", { name: "qa-created" })).toBeAttached();

  const mcpToggle = page.locator("label").filter({ hasText: "MCP Tools" }).getByRole("checkbox");
  await mcpToggle.uncheck();
  await expect(page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "MCP Tools" })).toBeHidden();
  await mcpToggle.check();
  await expect(page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "MCP Tools" })).toBeVisible();
});
