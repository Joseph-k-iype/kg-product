import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("chat displays cited answers and generative facts, then clears on context switch", async ({
  page,
  request,
}) => {
  const catalog = await (await request.get("/api/products?limit=200")).json();
  const p = catalog.items.find(
    (p: { name: string; active_release_id: string }) =>
      p.name.startsWith("Journey ") && p.active_release_id,
  );
  const published = p.revisions.find(
    (revision: { state: string }) => revision.state === "published",
  );
  await page.route(`**/products/${p.id}/chat?*`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "text/plain",
      body: "Customers can request refunds within 30 days of purchase. [S1]",
    }),
  );
  await page.route(`**/products/${p.id}/chat/runs/*`, (route) =>
    route.fulfill({
      json: {
        id: new URL(route.request().url()).pathname.split("/").at(-1),
        state: "complete",
        revision_id: published.id,
        release_id: p.active_release_id,
        generation: published.generation,
        label: "Published release",
        model: "deepseek/deepseek-v3.2",
        error: null,
        ui: {
          $type: "Card",
          title: "Policy summary",
          description: "Based on the cited evidence",
          children: [
            { $type: "Fact", label: "Refund window", value: "30 days" },
          ],
        },
        sources: [
          {
            citation: "S1",
            chunk_id: "test-evidence",
            document_id: "test-document",
            document_name: "Refund guide",
            source_url: "/api/documents/test-document/original",
            text: "Refunds within 30 days of purchase.",
            start: 0,
            end: 36,
            score: 0.9,
          },
        ],
      },
    }),
  );
  await page.goto("/chat");
  await page
    .getByLabel("Knowledge product", { exact: true })
    .selectOption(p.id);
  await page
    .getByLabel("Version to inspect", { exact: true })
    .selectOption(published.id);
  await expect(
    page.getByRole("heading", { name: "AI chat", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Message the assistant")
    .fill("What is the refund window?");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(page.getByText("30 days", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Based on the cited evidence", { exact: true }),
  ).toBeVisible();
  await page.getByText("S1 · Refund guide", { exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Open Refund guide", exact: true }),
  ).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({
    path: "../docs/screenshots/ai-chat.png",
    fullPage: true,
  });
  const other = catalog.items.find((item: { id: string }) => item.id !== p.id);
  await page
    .getByLabel("Knowledge product", { exact: true })
    .selectOption(other.id);
  await expect(
    page.getByText("What is the refund window?", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "Open Refund guide", exact: true }),
  ).toHaveCount(0);
});

test("chat fits a narrow viewport and explains how clearing stops an answer", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/chat");
  await expect(
    page.getByRole("heading", { name: "AI chat", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Clear conversation", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

test("a refused follow-up cannot borrow the previous answer's evidence", async ({
  page,
  request,
}) => {
  const catalog = await (await request.get("/api/products?limit=200")).json();
  const p = catalog.items.find(
    (p: { name: string; active_release_id: string }) =>
      p.name.startsWith("Journey ") && p.active_release_id,
  );
  const revision = p.revisions.find(
    (r: { state: string }) => r.state === "published",
  );
  let successfulId = "",
    turn = 0;
  await page.route(`**/products/${p.id}/chat?*`, (route) => {
    if (++turn === 1) {
      const query = new URL(route.request().url()).searchParams;
      successfulId =
        query.get("request_id") || query.get("conversation_id") || "";
      return route.fulfill({
        status: 200,
        contentType: "text/plain",
        body: "Refunds are available for thirty days. [S1]",
      });
    }
    return route.fulfill({ status: 409, json: { detail: "Not prepared" } });
  });
  await page.route(`**/products/${p.id}/chat/runs/*`, (route) => {
    const id = new URL(route.request().url()).pathname.split("/").at(-1);
    return id === successfulId
      ? route.fulfill({
          json: {
            id,
            state: "complete",
            revision_id: revision.id,
            release_id: p.active_release_id,
            generation: revision.generation,
            label: "Published release",
            model: "DeepSeek",
            error: null,
            sources: [],
            ui: { $type: "Fact", label: "Refund window", value: "30 days" },
          },
        })
      : route.fulfill({ status: 404, json: { detail: "No answer" } });
  });
  await page.goto(`/products/${p.id}/chat`);
  await page.getByLabel("Version to inspect").selectOption(revision.id);
  await page
    .getByLabel("Message the assistant")
    .fill("What is the refund window?");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(page.getByText("30 days", { exact: true })).toBeVisible();
  await page.getByLabel("Message the assistant").fill("A follow-up that fails");
  const metadata = page.waitForResponse((r) => r.url().includes("/chat/runs/"));
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await metadata;
  await expect(
    page.getByText("The assistant could not start.", { exact: false }),
  ).toBeVisible();
  await expect(page.getByText("30 days", { exact: true })).toHaveCount(1);
});

test("model Markdown cannot load outbound images", async ({
  page,
  request,
}) => {
  const catalog = await (await request.get("/api/products?limit=200")).json();
  const p = catalog.items.find(
    (p: { name: string; active_release_id: string }) =>
      p.name.startsWith("Journey ") && p.active_release_id,
  );
  let outbound = 0;
  await page.route("https://example.invalid/**", (route) => {
    outbound++;
    return route.abort();
  });
  await page.route(`**/products/${p.id}/chat?*`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "text/plain",
      body: "Answer ready. ![source image](https://example.invalid/pixel?data=synthetic-document-text)",
    }),
  );
  await page.route(`**/products/${p.id}/chat/runs/*`, (route) =>
    route.fulfill({ status: 404, json: { detail: "No display" } }),
  );
  await page.goto(`/products/${p.id}/chat`);
  await page.getByLabel("Message the assistant").fill("Show the answer");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(page.getByText("Answer ready.", { exact: false })).toBeVisible();
  await expect(page.locator(".chat-assistant img")).toHaveCount(0);
  expect(outbound).toBe(0);
});
