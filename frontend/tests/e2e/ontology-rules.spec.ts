import { test, expect } from "@playwright/test";

test("editing a minimum-only rule preserves its unbounded maximum", async ({
  page,
}) => {
  const created = await page.request.post("/api/products", {
    data: { name: "Unbounded rule " + Date.now() },
  });
  expect(created.status()).toBe(201);
  const product = await created.json();
  const imported = await page.request.post(
    `/api/products/${product.id}/ontology/import`,
    {
      data: {
        turtle: `@prefix ex: <https://rules.example/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
ex:Person a owl:Class; rdfs:label "Person" .
ex:name a owl:DatatypeProperty; rdfs:label "Name" .
ex:PersonShape a sh:NodeShape; sh:targetClass ex:Person;
  sh:property [sh:path ex:name; sh:minCount 1] .`,
      },
    },
  );
  expect(imported.status()).toBe(200);
  await page.goto(`/products/${product.id}/concepts`);
  await page
    .getByRole("button", { name: "Business Rules", exact: true })
    .click();
  await page.locator(".concept-item").click();
  await expect(page.getByLabel("Maximum values", { exact: true })).toHaveValue(
    "",
  );
  await page.getByLabel("Minimum values", { exact: true }).fill("2");
  await page
    .getByRole("button", { name: "Save business rule", exact: true })
    .click();
  await expect(
    page.getByText("Concepts and rules saved", { exact: true }),
  ).toBeVisible();
  const ontology = await page.request.get(
    `/api/products/${product.id}/ontology`,
  );
  const rules = (await ontology.json()).shapes;
  expect(rules).toHaveLength(1);
  expect(rules[0].min_count).toBe(2);
  expect(rules[0].max_count).toBeNull();
});
