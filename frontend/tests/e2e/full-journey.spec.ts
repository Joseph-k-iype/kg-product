import { test, expect } from "@playwright/test";
test("create, prepare, check, approve, publish and retrieve source evidence", async ({
  page,
}) => {
  const name = "Journey " + Date.now();
  await page.goto("/products/new");
  await page.getByLabel("Product name").fill(name);
  await page
    .getByLabel("Business purpose")
    .fill("Trusted refund guidance for customer support");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Add files", { exact: true }).setInputFiles({
    name: "refund-guide.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(
      "Complaint C-1042 submitted by Customer A-203. Customers can request refunds within 30 days of purchase.",
    ),
  });
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Concept starter").selectOption("customer-support");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Create draft", exact: true }).click();
  await expect(page.getByText("Draft created", { exact: true })).toBeVisible();
  await page
    .getByRole("navigation", { name: "Product sections" })
    .getByRole("link", { name: "Prepare Knowledge", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Run preparation", exact: true })
    .click();
  await expect(
    page.getByText("1 evidence excerpts · 1 searchable", { exact: true }),
  ).toBeVisible({ timeout: 60000 });
  await page
    .getByRole("navigation", { name: "Product sections" })
    .getByRole("link", { name: "Quality Checks", exact: true })
    .click();
  await page.getByRole("button", { name: "Run checks", exact: true }).click();
  await expect(
    page.getByText("No findings for this run.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Product sections" })
    .getByRole("link", { name: "Approvals", exact: true })
    .click();
  await page
    .getByLabel("Change summary")
    .fill("Verified refund guidance with source evidence");
  await page
    .getByRole("button", { name: "Request approval", exact: true })
    .click();
  await page.getByLabel("Demo identity").selectOption("Demo reviewer");
  await page
    .getByRole("button", { name: "Review changes", exact: true })
    .first()
    .click();
  await page
    .getByLabel("Decision reason")
    .fill("Verified the refund policy evidence");
  await page
    .getByRole("button", { name: "Approve revision", exact: true })
    .click();
  await page.getByRole("button", { name: "Publish", exact: true }).click();
  await expect(
    page.getByText("Release published", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Product sections" })
    .getByRole("link", { name: "Search", exact: true })
    .click();
  await page
    .getByLabel("Search version")
    .selectOption({ label: "Published release 1 · Active" });
  await page
    .getByLabel("Your question")
    .fill("How long do I have to ask for my money back?");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  const evidencePanel = page.locator("section").filter({
    has: page.getByRole("heading", {
      name: "Supporting evidence",
      exact: true,
    }),
  });
  await expect(
    evidencePanel.getByRole("link", { name: "Open source", exact: true }),
  ).toBeVisible({ timeout: 45000 });
  const sourceUrl = await evidencePanel
    .getByRole("link", { name: "Open source", exact: true })
    .getAttribute("href");
  expect(await (await page.request.get(sourceUrl!)).text()).toContain(
    "30 days",
  );
  const resultsPanel = page.locator("section").filter({
    has: page.getByRole("heading", {
      name: "1 evidence results",
      exact: true,
    }),
  });
  await expect(
    resultsPanel.getByText("Published release", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Open a draft", exact: true }),
  ).toBeVisible();
});

test("search evidence is cleared when switching product context", async ({
  page,
  request,
}) => {
  const catalog = await (await request.get("/api/products")).json();
  const a = catalog.items.find(
    (p: { name: string }) => p.name === "HR Policies",
  );
  const b = catalog.items.find(
    (p: { name: string }) => p.name === "Customer Complaints",
  );
  await page.goto("/retrieval");
  await page
    .getByLabel("Knowledge product", { exact: true })
    .selectOption(a.id);
  await page.getByLabel("Your question").fill("How many days of paid leave?");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "1 evidence results", exact: true }),
  ).toBeVisible({ timeout: 45000 });
  await page
    .getByLabel("Knowledge product", { exact: true })
    .selectOption(b.id);
  await expect(
    page.getByRole("heading", { name: "Search your knowledge", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "1 evidence results", exact: true }),
  ).toHaveCount(0);
});

test("a correction records the published version being inspected", async ({
  page,
  request,
}) => {
  const catalog = await (await request.get("/api/products")).json();
  const p = catalog.items.find(
    (p: { name: string; active_release_id: string }) =>
      p.name.startsWith("Journey ") && p.active_release_id,
  );
  const releases = await (
    await request.get("/api/products/" + p.id + "/releases")
  ).json();
  await request.post("/api/products/" + p.id + "/draft");
  await request.post("/api/products/" + p.id + "/graph/build");
  await page.goto("/products/" + p.id + "/explorer");
  await page
    .getByLabel("Version to inspect")
    .selectOption(releases[0].revision_id);
  await page
    .getByRole("row")
    .filter({ hasText: "Complaint C-1042" })
    .getByRole("button", { name: "Inspect evidence" })
    .click();
  await page
    .getByLabel("Flag a correction")
    .fill("Check which customer submitted this complaint");
  const sent = page.waitForRequest(
    (r) => r.url().includes("/flags") && r.method() === "POST",
  );
  await page.getByRole("button", { name: "Flag for review" }).click();
  expect(new URL((await sent).url()).searchParams.get("revision_id")).toBe(
    releases[0].revision_id,
  );
});
