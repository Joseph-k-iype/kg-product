import { test, expect } from "@playwright/test";

test("reduced motion keeps the decorative shader still and primary actions usable", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/overview");
  const art = page.locator(".knowledge-signal");
  await expect(art).toBeVisible();
  await expect(art).toHaveAttribute("aria-hidden", "true");
  await page.evaluate(() => document.fonts.ready);
  const first = await art.screenshot();
  await page.waitForTimeout(200);
  expect(await art.screenshot()).toEqual(first);
  await page
    .getByRole("link", { name: "New knowledge product", exact: true })
    .click();
  await expect(page.getByLabel("Product name")).toBeVisible();
});

test("the dashboard retains its artwork and workflows when WebGL is unavailable", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      type: string,
      ...args: unknown[]
    ) {
      if (
        type === "webgl" ||
        type === "webgl2" ||
        type === "experimental-webgl"
      )
        return null;
      return Reflect.apply(original, this, [type, ...args]);
    } as typeof original;
  });
  await page.goto("/overview");
  await expect(page.locator(".knowledge-signal")).toBeVisible();
  await expect(page.locator(".signal-fallback")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Your knowledge, ready to use." }),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Knowledge Products", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Knowledge products", exact: true }),
  ).toBeVisible();
});
