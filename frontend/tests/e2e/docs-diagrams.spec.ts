import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const files = execFileSync("git", ["ls-files", "*.md"], { cwd: root })
  .toString()
  .trim()
  .split("\n");
const diagrams = files.flatMap((file) =>
  [
    ...readFileSync(resolve(root, file), "utf8").matchAll(
      /^```mermaid\s*\n([\s\S]*?)^```/gm,
    ),
  ].map((match, index) => ({ file, index, source: match[1] })),
);

for (const { file, index, source } of diagrams) {
  test(`Mermaid renders ${file} diagram ${index + 1}`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto("/tests/fixtures/mermaid.html");
    const result = await page.evaluate(
      async ({ source, id }) => {
        // Vite serves the installed browser bundle; no CDN/provider network is used.
        const { default: mermaid } =
          // @ts-expect-error Browser-only module URL is served by the dev server.
          await import("/node_modules/mermaid/dist/mermaid.esm.min.mjs");
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: "neutral",
        });
        await mermaid.parse(source);
        const { svg } = await mermaid.render(id, source);
        document.getElementById("diagram")!.innerHTML = svg;
        const element = document.querySelector("svg")!;
        const viewBox = element
          .getAttribute("viewBox")!
          .split(/\s+/)
          .map(Number);
        return {
          viewBox,
          labels: element.querySelectorAll("text, foreignObject").length,
        };
      },
      { source, id: `diagram-${index}` },
    );
    expect(result.labels).toBeGreaterThan(0);
    expect(result.viewBox.every(Number.isFinite)).toBe(true);
    expect(result.viewBox[2]).toBeGreaterThan(0);
    expect(result.viewBox[3]).toBeGreaterThan(0);
    await expect(page.locator("svg")).toBeVisible();
    expect(await page.locator("svg").textContent()).not.toContain(
      "Syntax error",
    );
    expect(errors).toEqual([]);
    const path = resolve(
      root,
      ".improve/diagram-qa",
      `${file.replaceAll("/", "-")}-${index + 1}.png`,
    );
    mkdirSync(dirname(path), { recursive: true });
    await page.screenshot({ path, fullPage: true });
  });
}
