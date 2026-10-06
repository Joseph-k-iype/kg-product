import { test, expect, type APIRequestContext } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function publishedProduct(request: APIRequestContext) {
  const response = await request.get("/api/products?q=Journey%20&limit=200");
  const catalog = await response.json();
  const product = catalog.items.find(
    (item: { active_release_id: string }) => item.active_release_id,
  );
  expect(product).toBeTruthy();
  const releases = await (
    await request.get(`/api/products/${product.id}/releases`)
  ).json();
  return { ...product, revisionId: releases[0].revision_id };
}

test("published product screens retain context, load real data, and are accessible", async ({
  page,
  request,
}) => {
  const product = await publishedProduct(request);
  const errors: string[] = [];
  const serverErrors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => {
    if (response.url().includes("/api/") && response.status() >= 500)
      serverErrors.push(`${response.status()} ${response.url()}`);
  });
  await page.goto(`/products/${product.id}/overview`);
  await page.getByLabel("Version to inspect").selectOption(product.revisionId);
  for (const label of [
    "Overview",
    "Documents",
    "Concepts & Rules",
    "Explore Knowledge",
    "Prepare Knowledge",
    "Quality Checks",
    "Approvals",
    "Search",
    "Evidence Trail",
    "Connected Apps",
    "Release Activity",
    "AI Chat",
  ]) {
    await page
      .getByRole("navigation", { name: "Product sections" })
      .getByRole("link", { name: label, exact: true })
      .click();
    await expect(page.getByLabel("Version to inspect")).toHaveValue(
      product.revisionId,
    );
    await expect(
      page.getByText("Loading your workspace…", { exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("alert").filter({
        hasText:
          /Internal server error|Unable to complete|Service unavailable/i,
      }),
    ).toHaveCount(0);
    const accessibility = await new AxeBuilder({ page }).analyze();
    expect(accessibility.violations, label).toEqual([]);
  }
  expect(errors).toEqual([]);
  expect(serverErrors).toEqual([]);
});

test("connected app can follow, pin, and return to the active release", async ({
  page,
  request,
}) => {
  const product = await publishedProduct(request);
  const name = `QA copilot ${Date.now()}`;
  await page.goto(`/products/${product.id}/consumers`);
  await page.getByRole("button", { name: "Register app", exact: true }).click();
  await page.getByLabel("Application name").fill(name);
  await page.getByLabel("Application type").selectOption("copilot");
  await page
    .getByRole("button", { name: "Save application", exact: true })
    .click();
  const row = page.getByRole("row").filter({ hasText: name });
  await expect(row).toContainText("Follow active release");
  await expect(row).toContainText("Release 1");
  await row.getByRole("button", { name: "Edit policy" }).click();
  await page
    .getByLabel("Release policy", { exact: true })
    .selectOption("pinned");
  await page
    .getByLabel("Pinned release")
    .selectOption(product.active_release_id);
  await page
    .getByRole("button", { name: "Save application", exact: true })
    .click();
  await expect(row).toContainText("Pinned release");
  await page.reload();
  await expect(row).toContainText("Pinned release");
  await row.getByRole("button", { name: "Edit policy" }).click();
  await page
    .getByLabel("Release policy", { exact: true })
    .selectOption("active");
  await page
    .getByRole("button", { name: "Save application", exact: true })
    .click();
  await expect(row).toContainText("Follow active release");
  const consumers = await (
    await request.get(`/api/consumers?product_id=${product.id}`)
  ).json();
  const consumer = consumers.find(
    (item: { name: string }) => item.name === name,
  );
  expect(consumer.release_id).toBeNull();
  expect(
    (await (await request.get(`/api/consumers/${consumer.id}/resolve`)).json())
      .release_id,
  ).toBe(product.active_release_id);
});
