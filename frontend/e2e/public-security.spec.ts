import { expect, test } from "@playwright/test";

const banned = [
  "ownerUserId",
  "dossierId",
  "mediaAssetId",
  "cloudinaryPublicId",
  "objectKey",
  "reporterEmail",
  "reviewerNote",
  "privateKey",
  "restricted/source",
];

test("public visibility and leakage release gate", async ({ page }) => {
  const visible = await page.request.get(
    "/api/v1/public/works/bo-nhan-dien-tmi",
  );
  expect(visible.status()).toBe(200);
  expect(visible.headers()["cache-control"]).toBe("no-store");
  const publicJson = await visible.text();
  for (const field of banned) expect(publicJson).not.toContain(field);

  const hiddenPaths = [
    "tai-san-rieng-tu",
    "tai-san-da-dinh-chi",
    "11111111-1111-4111-8111-111111111111",
  ];
  const hiddenResponses = await Promise.all(
    hiddenPaths.map((slug) => page.request.get(`/api/v1/public/works/${slug}`)),
  );
  expect(hiddenResponses.map((response) => response.status())).toEqual([
    404, 404, 404,
  ]);
  const hiddenBodies = await Promise.all(
    hiddenResponses.map((response) => response.text()),
  );
  expect(new Set(hiddenBodies).size).toBe(1);
  for (const response of hiddenResponses) {
    expect(response.headers()["cache-control"]).toBe("no-store");
  }

  const unlisted = await page.request.get("/api/v1/public/works/chia-se-rieng");
  expect(unlisted.status()).toBe(200);
  expect(unlisted.headers()["x-robots-tag"]).toContain("noindex");
  const sitemap = await page.request.get("/sitemaps/works/1.xml");
  expect(await sitemap.text()).not.toContain("chia-se-rieng");

  await page.goto("/works/bo-nhan-dien-tmi");
  const html = await page.locator("html").innerHTML();
  for (const field of banned) expect(html).not.toContain(field);
});
