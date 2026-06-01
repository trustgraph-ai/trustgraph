import { writeFileSync } from "node:fs";
import { expect, expectHeading, gotoWorkbench, test } from "./fixtures";

test("library searches, shows metadata, uploads small and chunked files, and deletes", async ({ page }, testInfo) => {
  await gotoWorkbench(page, "/library");
  await expectHeading(page, "Library");
  await expect(page.getByText("QA Document")).toBeVisible();

  await page.getByPlaceholder("Search documents...").fill("missing");
  await expect(page.getByText("No documents match your search.")).toBeVisible();
  await page.getByPlaceholder("Search documents...").fill("QA");
  await expect(page.getByText("QA Document")).toBeVisible();

  await page.getByLabel("View QA Document").click();
  await expect(page.getByRole("dialog", { name: "Document Details" })).toBeVisible();
  await expect(page.getByText("Seeded document for browser QA")).toBeVisible();
  await page.getByLabel("Close dialog").click();

  const smallFile = testInfo.outputPath("qa-upload-small.txt");
  writeFileSync(smallFile, "Small QA upload");
  await page.getByRole("button", { name: "Upload", exact: true }).click();
  const uploadDialog = page.getByRole("dialog", { name: "Upload Document" });
  await expect(uploadDialog).toBeVisible();
  await page.locator('input[type="file"]').setInputFiles(smallFile);
  await expect(uploadDialog.getByRole("textbox", { name: "Title" })).toHaveValue("qa-upload-small");
  await uploadDialog.getByRole("button", { name: "Upload" }).click();
  await expect(uploadDialog).toBeHidden();
  await expect(page.getByRole("row", { name: /qa-upload-small/ })).toBeVisible();

  const chunkedFile = testInfo.outputPath("qa-upload-chunked.txt");
  writeFileSync(chunkedFile, "chunked ".repeat(180_000));
  await page.getByRole("button", { name: "Upload", exact: true }).click();
  const chunkedDialog = page.getByRole("dialog", { name: "Upload Document" });
  await page.locator('input[type="file"]').setInputFiles(chunkedFile);
  await expect(chunkedDialog.getByRole("textbox", { name: "Title" })).toHaveValue("qa-upload-chunked");
  await chunkedDialog.getByRole("button", { name: "Upload" }).click();
  await expect(page.getByRole("row", { name: /qa-upload-chunked/ })).toBeVisible();

  await page.getByLabel("Delete qa-upload-small").click();
  const deleteDialog = page.getByRole("dialog", { name: "Delete Document" });
  await expect(deleteDialog).toBeVisible();
  await deleteDialog.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(page.getByRole("row", { name: /qa-upload-small/ })).toBeHidden();
});
