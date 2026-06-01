import { expect, expectHeading, gotoWorkbench, test } from "./fixtures";

test("flows validate parameters, start, expand, and stop", async ({ page }) => {
  await gotoWorkbench(page, "/flows");
  await expectHeading(page, "Flows");
  await expect(page.getByRole("button", { name: /qa-flow Seeded QA flow/ })).toBeVisible();

  await page.getByRole("button", { name: "Start Flow" }).click();
  const dialog = page.getByRole("dialog", { name: "Start Flow" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Start" }).click();
  await expect(page.getByText("Flow ID is required")).toBeVisible();

  await dialog.getByPlaceholder("my-flow-id").fill("qa-started");
  await dialog.locator("select").selectOption("qa-blueprint");
  await dialog.getByPlaceholder("What this flow does").fill("Started from browser QA");
  await dialog.getByText("Blueprint Details").click();
  await expect(dialog.locator("pre")).toContainText("qa-blueprint");
  await dialog.locator("textarea").fill("{bad");
  await dialog.getByRole("button", { name: "Start" }).click();
  await expect(page.getByText("Invalid JSON")).toBeVisible();

  await dialog.locator("textarea").fill('{"temperature":0.2}');
  await dialog.getByRole("button", { name: "Start" }).click();
  await expect(dialog).toBeHidden();
  const startedFlow = page.getByRole("button", { name: /qa-started Started from browser QA/ });
  await expect(startedFlow).toBeVisible();

  await startedFlow.click();
  await expect(page.locator("pre").last()).toContainText("Started from browser QA");
  await page.getByLabel("Stop flow qa-started").click();
  await expect(startedFlow).toBeHidden();
});

test("knowledge cores load and delete with confirmation", async ({ page }) => {
  await gotoWorkbench(page, "/knowledge-cores");
  await expectHeading(page, "Knowledge Cores");
  await expect(page.getByRole("row", { name: /qa-core/ })).toBeVisible();

  await page.getByLabel("Load core qa-core").click();
  await expect(page.getByText("Core loaded")).toBeVisible();

  await page.getByLabel("Delete core qa-core").click();
  const dialog = page.getByRole("dialog", { name: "Delete Knowledge Core" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();

  await page.getByLabel("Delete core qa-core").click();
  await dialog.getByRole("button", { name: "Delete" }).click();
  await expect(page.getByRole("row", { name: /qa-core/ })).toBeHidden();
});
