import { expect, expectCanvasNonBlank, expectHeading, gotoWorkbench, test } from "./fixtures";

test("chat streams, cancels, regenerates, copies, and clears messages", async ({ page }) => {
  await gotoWorkbench(page, "/chat", { chat: { delayFrames: 6 } });
  await expectHeading(page, "Chat");

  await page.getByPlaceholder(/Ask using Graph RAG/).fill("cancel this request");
  await page.getByLabel("Send message").click();
  await expect(page.getByLabel("Cancel request")).toBeVisible();
  await page.getByLabel("Cancel request").click();
  await expect(page.getByText("(Cancelled)")).toBeVisible();

  await page.getByLabel("Clear conversation").click();
  await expect(page.getByText("Start a conversation with TrustGraph.")).toBeVisible();

  await page.getByPlaceholder(/Ask using Graph RAG/).fill("Who does Alice know?");
  await page.getByLabel("Send message").click();
  await expect(page.getByText(/Mock graph answer from QA knowledge graph/)).toBeVisible();
  await expect(page.getByText("qa-model")).toBeVisible();

  await page.getByText(/Mock graph answer/).hover();
  await page.getByLabel("Copy message").click();
  await expect.poll(() => page.evaluate(() => (window as Window & { __TRUSTGRAPH_WORKBENCH_CLIPBOARD__?: string }).__TRUSTGRAPH_WORKBENCH_CLIPBOARD__)).toContain("Mock graph answer");

  await page.getByLabel("Regenerate response").click();
  await expect(page.getByText(/Mock graph answer from QA knowledge graph/).last()).toBeVisible();

  await page.getByText("Agent").click();
  await page.getByPlaceholder(/Ask using Agent/).fill("Use the agent");
  await page.getByLabel("Send message").click();
  await expect(page.getByText("Thinking")).toBeVisible();
  await expect(page.getByText("Observing")).toBeVisible();
  await expect(page.getByText("Mock agent answer from TrustGraph.")).toBeVisible();
});

test("graph renders seeded triples and responds to controls", async ({ page }) => {
  await gotoWorkbench(page, "/graph");
  await expectHeading(page, "Graph");
  await expect(page.getByText(/nodes/).first()).toBeVisible();
  await expect(page.getByText(/edges/).first()).toBeVisible();

  await expectCanvasNonBlank(page.locator("canvas").first());

  await page.getByPlaceholder("Search graph...").fill("Alice");
  await expect(page.getByText(/1 nodes/)).toBeVisible();
  await page.getByRole("button", { name: "Labels" }).click();
  await page.getByLabel("Node limit").selectOption("100");
  await expect(page.getByText(/nodes/).first()).toBeVisible();
});
