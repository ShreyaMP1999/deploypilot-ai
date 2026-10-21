// Run against fresh seeded servers. DEMO_PASSWORD must match the backend seed.
import { chromium, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
const password = process.env.DEMO_PASSWORD;
if (!password) throw new Error("Set DEMO_PASSWORD to the seeded password");
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1512, height: 1100 },
  deviceScaleFactor: 1,
});
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
const out = process.env.SCREENSHOT_DIR || "../../demo";
await mkdir(out, { recursive: true });
try {
  await page.goto(process.env.WEB_URL || "http://localhost:3000");
  await page.getByLabel("Username", { exact: true }).fill("pilot");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Your AI operations, in focus." }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Workflow Studio", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Execute workflow", exact: true })
    .click();
  await expect(page.locator(".inspector-status .badge")).toHaveText(
    "awaiting approval",
  );
  await page.screenshot({ path: `${out}/workflow-studio.png`, fullPage: true });
  await page
    .getByRole("button", { name: "Approval Center", exact: false })
    .click();
  await page
    .getByRole("button", { name: "Approve & process", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Approval recorded");
  await expect(page.locator(".inspector-status .badge")).toHaveText(
    "completed",
  );
  await expect(
    page.getByRole("button", { name: "Approve & process", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Workflow Studio", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Automatic example", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Execute workflow", exact: true })
    .click();
  await expect(page.locator(".inspector-status .badge")).toHaveText(
    "completed",
  );
  await page
    .getByRole("button", { name: "Approval example", exact: true })
    .click();
  await page
    .getByLabel("Source record", { exact: true })
    .selectOption("ORD-1003");
  await page
    .getByRole("button", { name: "Execute workflow", exact: true })
    .click();
  await expect(page.locator(".inspector-status .badge")).toHaveText(
    "awaiting approval",
  );
  await page.getByRole("button", { name: "Evaluations", exact: true }).click();
  await page
    .getByRole("button", { name: "Run policy suite", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("evaluation completed");
  await expect(page.getByText("30/30", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page.screenshot({ path: `${out}/overview.png`, fullPage: true });
  await page
    .getByLabel("Active customer", { exact: true })
    .selectOption("orbit");
  await expect(page.locator(".context-strip strong")).toHaveText(
    "OrbitCloud SaaS",
  );
  await page
    .getByRole("button", { name: "Workflow Studio", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Execute workflow", exact: true })
    .click();
  await expect(page.locator(".inspector-status .badge")).toHaveText(
    "awaiting approval",
  );
  await page
    .getByRole("button", { name: "Approval Center", exact: false })
    .click();
  await expect(
    page.getByText("security review", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Approve & process", exact: true })
    .click();
  await expect(page.locator(".inspector-status .badge")).toHaveText(
    "completed",
  );
  await page
    .getByRole("button", { name: "Workflow Studio", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Automatic example", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Execute workflow", exact: true })
    .click();
  await expect(page.locator(".inspector-status .badge")).toHaveText(
    "completed",
  );
  await page
    .getByRole("button", { name: "Execution Logs", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: /TKT-2002/ }).first(),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: /ORD-1001/ })).toHaveCount(0);
  await page.getByRole("button", { name: "Customers", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "OrbitCloud SaaS configuration" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page.screenshot({ path: `${out}/orbit-overview.png`, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: `${out}/mobile.png`, fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
  console.log(
    "PASS: login, refund approval, automatic refund, security escalation, documentation draft, tenant switch, configurations, logs, evaluations and mobile layout.",
  );
} finally {
  await browser.close();
}
