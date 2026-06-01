import { expect, expectHeading, gotoWorkbench, test } from "./fixtures";

test("prompts and token costs render seeded config", async ({ page }) => {
  await gotoWorkbench(page, "/prompts");
  await expectHeading(page, "Prompts");
  await expect(page.getByRole("tab", { name: "Templates" })).toHaveAttribute("aria-selected", "true");
  await page.getByRole("button", { name: "qa-template" }).click();
  await expect(page.getByText("QA template system")).toBeVisible();
  await expect(page.getByText("Answer the QA question")).toBeVisible();
  await page.getByLabel("Close prompt detail").click();
  await page.getByRole("tab", { name: "System Prompt" }).click();
  await expect(page.getByText("You are the QA system prompt.")).toBeVisible();

  await page.goto("/token-cost");
  await expectHeading(page, "Token Cost");
  await expect(page.getByText("qa-model")).toBeVisible();
  await expect(page.getByText("$1.25")).toBeVisible();
  await expect(page.getByText("$2.50")).toBeVisible();
});

test("mcp tools add, validate, edit, and delete servers and tools", async ({ page }) => {
  await gotoWorkbench(page, "/mcp-tools");
  await expectHeading(page, "MCP Tools");
  const main = page.locator("#main-content");
  await expect(main.getByText("qa-search")).toBeVisible();

  await page.getByRole("button", { name: "Add Server" }).click();
  let dialog = page.getByRole("dialog", { name: "Add MCP Server" });
  await dialog.getByLabel("Key").fill("qa-extra-server");
  await dialog.getByLabel("URL").fill("http://localhost:8383/mcp-extra");
  await dialog.getByLabel("Remote Name").fill("qa-extra");
  const authToken = dialog.getByRole("textbox", { name: /Auth Token/ });
  await authToken.fill("token");
  await dialog.getByLabel("Show auth token").click();
  await expect(authToken).toHaveAttribute("type", "text");
  await dialog.getByRole("button", { name: "Save" }).click();
  await expect(main.getByText("qa-extra-server")).toBeVisible();

  await page.getByRole("button", { name: "Add Server" }).click();
  dialog = page.getByRole("dialog", { name: "Add MCP Server" });
  await dialog.getByLabel("Key").fill("qa-search");
  await dialog.getByLabel("URL").fill("http://localhost:8383/duplicate");
  await dialog.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("A server with this key already exists")).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel" }).click();

  await page.getByRole("button", { name: /Tools/ }).click();
  await page.getByRole("button", { name: "Add Tool" }).click();
  dialog = page.getByRole("dialog", { name: "Add MCP Tool" });
  await dialog.getByLabel("Key").fill("qa-extra-tool");
  await dialog.getByLabel("Name").fill("QA Extra Tool");
  await dialog.getByLabel("Description").fill("Extra tool from browser QA");
  await dialog.getByLabel("MCP Server").selectOption("qa-extra-server");
  await dialog.getByLabel("Groups").fill("default, qa");
  await dialog.getByRole("button", { name: "Add" }).click();
  await dialog.getByPlaceholder("name").fill("query");
  await dialog.getByPlaceholder("description").fill("Query to execute");
  await dialog.getByRole("button", { name: "Save" }).click();
  await expect(main.getByText("qa-extra-tool")).toBeVisible();

  await page.getByLabel("Edit tool qa-extra-tool").click();
  dialog = page.getByRole("dialog", { name: "Edit MCP Tool" });
  await dialog.getByLabel("Name").fill("QA Extra Tool Edited");
  await dialog.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("QA Extra Tool Edited")).toBeVisible();

  await page.getByLabel("Delete tool qa-extra-tool").click();
  dialog = page.getByRole("dialog", { name: "Delete tool" });
  await dialog.getByRole("button", { name: "Delete" }).click();
  await expect(main.getByText("qa-extra-tool")).toBeHidden();

  await page.getByRole("button", { name: /Servers/ }).click();
  await page.getByLabel("Delete server qa-extra-server").click();
  dialog = page.getByRole("dialog", { name: "Delete server" });
  await dialog.getByRole("button", { name: "Delete" }).click();
  await expect(main.getByText("qa-extra-server")).toBeHidden();
});
