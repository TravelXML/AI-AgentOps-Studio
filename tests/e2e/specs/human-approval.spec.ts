import { expect, test } from "@playwright/test";

/**
 * Human Approval acceptance test (spec section 16): a run must genuinely pause at a Human
 * Approval node (LangGraph interrupt + Postgres checkpoint, not a frontend-only fake), then
 * resume to completion when approved via the trace page.
 *
 * Prerequisite: a flow named "Refund Approval" with Input -> Agent -> Human Approval -> Output
 * must already exist (see examples/human-approval-agent/flowspec.json). Import it via the
 * Flows page, or run `make seed`, before running this spec.
 */
test("run pauses for human approval and resumes to completion", async ({ page }) => {
  await page.goto("/flows");
  await page.locator("a", { hasText: "Refund Approval" }).first().click();
  await page.waitForTimeout(1500);

  await page.locator("button", { hasText: "run" }).first().click();
  const inputJson = page.getByText("Input JSON").locator("xpath=following-sibling::textarea[1]");
  await inputJson.fill('{\n  "amount": 900\n}');
  await page.locator("button", { hasText: "▶ Run" }).click();

  await expect(page.getByText("run.waiting")).toBeVisible({ timeout: 15_000 });

  const traceLink = page.locator("a", { hasText: "Open trace" });
  await traceLink.click();
  await expect(page.getByText("Waiting for human approval")).toBeVisible();

  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.locator("h1 ~ span", { hasText: "SUCCEEDED" })).toBeVisible({ timeout: 10_000 });
});
