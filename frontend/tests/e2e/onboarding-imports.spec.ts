import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("onboarding explains search settings and imports mixed business data", async ({
  page,
}) => {
  await page.goto("/products/new");
  await page.getByLabel("Product name").fill("Mixed onboarding " + Date.now());
  await page
    .getByLabel("Business purpose")
    .fill("Find customer records and policies");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Bring data", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Add files", { exact: true }).setInputFiles([
    {
      name: "customers.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("id,name\n1,Ana\n2,Ben\n"),
    },
    {
      name: "policy.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Customers have thirty days to request a refund."),
    },
    {
      name: "terms.ttl",
      mimeType: "text/turtle",
      buffer: Buffer.from(
        "@prefix ex: <https://terms.example/> . @prefix owl: <http://www.w3.org/2002/07/owl#> . ex:Policy a owl:Class .",
      ),
    },
  ]);
  await expect(page.getByText("2 records", { exact: true })).toBeVisible();
  await expect(
    page.getByText("1 concept · definitions only", { exact: true }),
  ).toBeVisible();
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
  await page.screenshot({
    path: "../docs/screenshots/bring-data.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(
    page.getByText("This is a search setting, not a readiness score.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByLabel("How many matching results?").selectOption("10");
  await page
    .getByRole("heading", { name: "Start with a purpose.", exact: true })
    .click();
  await page.screenshot({
    path: "../docs/screenshots/readiness.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(
    page.getByText("Up to 10 evidence matches per search", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Create draft", exact: true }).click();
  await expect(page.getByText("Draft created", { exact: true })).toBeVisible();
  const productId = new URL(page.url()).pathname.split("/")[2];
  const documents = await page.request.get(
    `/api/products/${productId}/documents`,
  );
  expect(
    (await documents.json())
      .map((d: { data_kind: string }) => d.data_kind)
      .sort(),
  ).toEqual(["csv", "definitions", "document"]);
});

test("a rejected structured file can be removed without losing the wizard", async ({
  page,
}) => {
  await page.goto("/products/new");
  await page.getByLabel("Product name").fill("Invalid import " + Date.now());
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Add files", { exact: true }).setInputFiles({
    name: "bad.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("id,id\n1,2"),
  });
  await expect(page.getByRole("alert")).toContainText("unique");
  await expect(
    page.getByRole("button", { name: "Continue", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Remove bad.csv", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Continue", exact: true }),
  ).toBeEnabled();
});
