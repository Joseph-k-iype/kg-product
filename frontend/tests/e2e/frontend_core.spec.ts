import { test, expect } from "@playwright/test";
test("business owner creates an incomplete draft and sees it after reload", async ({
  page,
}) => {
  await page.goto("/products");
  await page.getByRole("link", { name: "New knowledge product" }).click();
  await page.getByLabel("Product name").fill("Browser product " + Date.now());
  await page
    .getByLabel("Business purpose")
    .fill("Answer customer questions with trusted documents");
  for (let i = 0; i < 4; i++)
    await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Create draft", exact: true }).click();
  await expect(page.getByText("Draft created", { exact: true })).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("Add documents", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByLabel("Product lifecycle")).toBeVisible();
});
test("all business destinations open without losing product context", async ({
  page,
}) => {
  await page.goto("/overview");
  await expect(
    page.getByRole("heading", { name: "Your knowledge, ready to use." }),
  ).toBeVisible();
  for (const name of [
    "Documents & Sources",
    "Concepts & Rules",
    "Explore Knowledge",
    "Quality Checks",
    "Approvals",
    "Search Playground",
    "Evidence Trail",
    "Connected Apps",
  ]) {
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name, exact: true })
      .click();
    await expect(page.getByRole("main")).toBeVisible();
    await expect(
      page.getByRole("alert").filter({ hasText: "Internal server error" }),
    ).toHaveCount(0);
  }
});
