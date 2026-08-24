import { expect, test, type Locator, type Page } from "@playwright/test";

/**
 * The end-to-end acceptance test for the vertical slice (spec section 58):
 *
 *   Create flow -> Add Input -> Add Agent -> Add Output -> Save -> Run ->
 *   Observe node execution -> Receive output -> Open trace
 *
 * Uses MockLLM (the "default" model) exclusively, so this test requires no API key and runs
 * fully offline against a local API + Postgres. Requires the API (localhost:8000) and web
 * (localhost:3000) dev servers to already be running - see docs/development/local-development.md.
 */

async function dragNodeOntoCanvas(page: Page, canvas: Locator, nodeLabel: string, x: number, y: number) {
  const canvasBox = await canvas.boundingBox();
  if (!canvasBox) throw new Error("canvas not visible");
  const source = page.locator(`[draggable="true"]`, { hasText: nodeLabel }).first();
  await source.scrollIntoViewIfNeeded();
  const dataTransfer = await page.evaluateHandle(() => new DataTransfer());
  await source.dispatchEvent("dragstart", { dataTransfer });
  await canvas.dispatchEvent("dragover", {
    dataTransfer,
    clientX: canvasBox.x + x,
    clientY: canvasBox.y + y,
  });
  await canvas.dispatchEvent("drop", {
    dataTransfer,
    clientX: canvasBox.x + x,
    clientY: canvasBox.y + y,
  });
  await source.dispatchEvent("dragend", { dataTransfer });
}

async function connectHandles(page: Page, source: Locator, target: Locator) {
  const s = await source.boundingBox();
  const t = await target.boundingBox();
  if (!s || !t) throw new Error("handle not visible");
  await page.mouse.move(s.x + s.width / 2, s.y + s.height / 2);
  await page.mouse.down();
  await page.mouse.move(t.x + t.width / 2, t.y + t.height / 2, { steps: 20 });
  await page.mouse.up();
  await page.waitForTimeout(300);
}

test("simple agent flow: build, save, run, and open trace", async ({ page }) => {
  const flowName = `E2E Vertical Slice ${Date.now()}`;

  await test.step("create a new flow", async () => {
    await page.goto("/flows");
    await page.getByRole("button", { name: "New Flow" }).click();
    await page.getByPlaceholder("Flow name").fill(flowName);
    await page.getByRole("button", { name: "Create" }).click();
    await page.waitForURL(/\/flows\/.+/);
  });

  const canvas = page.locator(".react-flow__pane");
  await expect(canvas).toBeVisible();

  await test.step("add Input, Agent, and Output nodes", async () => {
    await dragNodeOntoCanvas(page, canvas, "Input", 90, 150);
    await dragNodeOntoCanvas(page, canvas, "Agent", 320, 150);
    await dragNodeOntoCanvas(page, canvas, "Output", 550, 150);
    await expect(page.locator(".react-flow__node")).toHaveCount(3);
  });

  await test.step("connect Input -> Agent -> Output", async () => {
    const inputNode = page.locator(".react-flow__node", { hasText: "Input" });
    const agentNode = page.locator(".react-flow__node", { hasText: "Agent" }).first();
    const outputNode = page.locator(".react-flow__node", { hasText: "Output" });

    await connectHandles(page, inputNode.locator(".react-flow__handle-right"), agentNode.locator(".react-flow__handle-left"));
    await connectHandles(page, agentNode.locator(".react-flow__handle-right"), outputNode.locator(".react-flow__handle-left"));
    await expect(page.locator(".react-flow__edge")).toHaveCount(2);
  });

  await test.step("configure the agent to use MockLLM", async () => {
    await page.locator(".react-flow__node", { hasText: "Agent" }).first().click();
    const instructions = page.getByText("System instructions").locator("xpath=following-sibling::textarea[1]");
    await instructions.fill("You are a helpful assistant for the AgentQ E2E test.");
    // "model" select already defaults to "default (MockLLM)" - no cloud credentials required.
  });

  await test.step("save the flow", async () => {
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("saved")).toBeVisible();
  });

  await test.step("run the flow and observe node execution", async () => {
    await page.locator("button", { hasText: "run" }).first().click();
    const inputJson = page.getByText("Input JSON").locator("xpath=following-sibling::textarea[1]");
    await inputJson.fill('{\n  "query": "Hello from the E2E test"\n}');
    await page.locator("button", { hasText: "▶ Run" }).click();
    await expect(page.getByText("run.completed")).toBeVisible({ timeout: 15_000 });
  });

  await test.step("receive output", async () => {
    await page.locator("button", { hasText: "output" }).first().click();
    await expect(page.locator("pre")).toContainText("Hello from the E2E test");
  });

  await test.step("open the trace and see steps + tokens", async () => {
    const traceLink = page.locator("a", { hasText: "Open trace" });
    await expect(traceLink).toBeVisible();
    await traceLink.click();
    await expect(page.getByText("Execution Steps")).toBeVisible();
    await expect(page.locator(".divide-y > button")).toHaveCount(3, { timeout: 10_000 });
    await expect(page.getByText(/SUCCEEDED/).first()).toBeVisible();
  });
});
