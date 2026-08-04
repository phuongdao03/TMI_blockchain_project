import { expect, test } from "@playwright/test";

test("public portal is professional, responsive and verifiable", async ({
  page,
}, testInfo) => {
  test.setTimeout(60_000);
  const consoleProblems: string[] = [];
  const searchHistoryRequests: string[] = [];
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleProblems.push(message.text());
    }
  });
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/me/search-history")) {
      searchHistoryRequests.push(request.url());
    }
  });

  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: /Niềm tin cho tài sản số/,
    }),
  ).toBeVisible();
  await expect(page.getByText("Bộ nhận diện TMI")).toBeVisible();
  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath("home.png"),
  });

  await page.goto("/thu-vien");
  await expect(
    page.getByRole("heading", { name: /Di sản được công bố/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Xem tác phẩm Bộ nhận diện TMI/ }).first(),
  ).toBeVisible();
  const autocompleteResponse = page.waitForResponse((response) =>
    response.url().includes("/api/v1/public/search/autocomplete?q=bo"),
  );
  const autocomplete = page.getByRole("combobox", { name: "Tìm tác phẩm" });
  await autocomplete.fill("bo");
  await autocompleteResponse;
  await expect(
    page.getByRole("listbox", { name: "Gợi ý tìm kiếm" }),
  ).toBeVisible();
  await autocomplete.press("ArrowDown");
  await autocomplete.press("Enter");
  await expect(page).toHaveURL(/\/tai-san\/bo-nhan-dien-tmi$/);
  await page.goto("/thu-vien");
  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath("public-catalog.png"),
  });

  await page.goto("/tim-kiem?q=bo&category=brand&sort=relevance");
  await expect(
    page.getByRole("heading", { name: /Tìm trong kho tài sản công khai/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Bỏ danh mục Thương hiệu/ }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Trang tiếp" })).toHaveAttribute(
    "href",
    /cursor=e2e-next-cursor/,
  );
  await expect(page.getByText("TMI-2026-7EAEC2D2C99A")).toBeVisible();
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
    "content",
    /noindex/,
  );
  await expect(page.getByText("Lịch sử đang tắt")).toHaveCount(0);
  await page.reload();
  await expect(page.getByLabel("Sắp xếp kết quả")).toHaveValue("relevance");
  await page.getByRole("link", { name: "Trang tiếp" }).click();
  await expect(page).toHaveURL(/cursor=e2e-next-cursor/);
  await page.goBack();
  await expect(page).toHaveURL(/q=bo&category=brand&sort=relevance$/);
  if (testInfo.project.name === "mobile-chrome") {
    await page.getByRole("button", { name: /Bộ lọc/ }).click();
    const closeSearchFilter = page.getByRole("button", { name: "Đóng bộ lọc" });
    await expect(closeSearchFilter).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();
  }
  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath("search-results.png"),
  });

  await page.goto("/thu-vien?category=brand&tag=featured&sort=popular");
  await expect(page.getByLabel("Sắp xếp")).toHaveValue("popular");
  await expect(page.getByLabel("Danh mục")).toHaveValue("brand");
  if (testInfo.project.name === "mobile-chrome") {
    await page.getByRole("button", { name: /Bộ lọc/ }).click();
    const closeFilter = page.getByRole("button", { name: "Đóng bộ lọc" });
    await expect(closeFilter).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();
  }

  await page.goto("/tai-san/bo-nhan-dien-tmi");
  await expect(
    page.getByRole("heading", { name: "Bộ nhận diện TMI" }),
  ).toBeVisible();
  await expect(page.getByText("Chưa có media công khai")).toBeVisible();
  await expect(page.getByText("Đã đối chiếu on-chain")).toBeVisible();
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    "href",
    "http://127.0.0.1:3100/tai-san/bo-nhan-dien-tmi",
  );
  await expect(page.locator('meta[property="og:title"]')).toHaveAttribute(
    "content",
    /Bộ nhận diện TMI/,
  );
  await page.getByRole("button", { name: "QR" }).click();
  await expect(
    page.getByRole("dialog", { name: "Quét để mở tác phẩm" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Đóng mã QR" })).toBeFocused();
  await expect(page.getByRole("link", { name: "Tải mã QR" })).toHaveAttribute(
    "href",
    "/api/v1/public/works/bo-nhan-dien-tmi/qr",
  );
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await page.getByRole("button", { name: "Báo cáo" }).click();
  await expect(
    page.getByRole("dialog", { name: "Báo cáo nội dung" }),
  ).toBeVisible();
  await page.getByLabel(/Lý do/).selectOption("INCORRECT_INFORMATION");
  await page.getByLabel("Mô tả bổ sung").fill("Thông tin cần được đối chiếu.");
  await page.getByLabel(/Email liên hệ/).fill("reporter@example.com");
  await page.getByRole("button", { name: "Gửi báo cáo" }).click();
  await expect(page.getByText("Đã tiếp nhận báo cáo")).toBeVisible();
  await page.getByRole("button", { name: "Hoàn tất" }).click();
  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath("public-work-detail.png"),
  });

  await page.goto("/tai-san/bo-nhan-dien-cu");
  await expect(page).toHaveURL(/\/tai-san\/bo-nhan-dien-tmi$/);

  await page.goto("/tai-san/chia-se-rieng");
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
    "content",
    /noindex/,
  );

  await page.goto("/kiem-tra");
  await page.getByPlaceholder("TMI-2026-…").fill("TMI-2026-7EAEC2D2C99A");
  await page.getByRole("button", { name: "Xác minh ngay" }).click();
  await expect(page.getByRole("heading", { name: "Hợp lệ" })).toBeVisible();

  const robots = await page.request.get("/robots.txt");
  expect(await robots.text()).toContain(
    "Sitemap: http://127.0.0.1:3100/sitemap.xml",
  );
  const sitemapIndex = await page.request.get("/sitemap.xml");
  expect(await sitemapIndex.text()).toContain("/sitemaps/works/1.xml");
  const worksSitemap = await page.request.get("/sitemaps/works/1.xml");
  const worksXml = await worksSitemap.text();
  expect(worksXml).toContain("/tai-san/bo-nhan-dien-tmi");
  expect(worksXml).not.toContain("chia-se-rieng");

  expect(consoleProblems).toEqual([]);
  expect(searchHistoryRequests).toEqual([]);
});
