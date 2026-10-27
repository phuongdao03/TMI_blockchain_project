import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("certificate sharing recovers when the browser denies clipboard access", async ({
  page,
}, info) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "share", {
      configurable: true,
      value: undefined,
    });
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: () =>
          Promise.reject(
            new DOMException("Permission denied", "NotAllowedError"),
          ),
      },
    });
  });
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/verify/demo-token");
  await page.getByRole("button", { name: "Chia sẻ", exact: true }).click();
  const link = page.getByLabel("Liên kết tra cứu để sao chép");
  await expect(link).toHaveValue(/\/verify\//);
  await link.focus();
  expect(
    await link.evaluate(
      (input: HTMLInputElement) =>
        input.selectionEnd === input.value.length && input.selectionStart === 0,
    ),
  ).toBe(true);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    accessibility.violations.map(({ id, nodes }) => ({
      id,
      targets: nodes.map((node) => node.target),
    })),
  ).toEqual([]);
  await page.screenshot({
    path: `../docs/ux-evidence-2026-10-27/share-recovery-${info.project.name}.png`,
    fullPage: true,
    scale: "css",
  });
  expect(errors).toEqual([]);
});

test("certificate issuer stays readable without mobile overflow", async ({
  page,
}) => {
  await page.goto("/verify/demo-token");
  const issuer = page
    .locator(".digital-certificate dd")
    .filter({ hasText: /^Đề cử Tinh Hoa Việt$/ });
  for (const width of [320, 390, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(issuer).toBeVisible();
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth + 1,
        ),
      )
      .toBe(true);
  }
});

test("public verification explains provenance without exposing internals", async ({
  page,
}) => {
  await page.goto("/verify/demo-token");

  await expect(
    page.getByText(
      "Đối chiếu tên tác phẩm, chủ thể và thời điểm xác nhận với thông tin bạn được cung cấp.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Lịch sử xác nhận" }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("listitem")
      .filter({ hasText: "Phiên bản 1" })
      .getByText("Phiên bản 1"),
  ).toBeVisible();
  await expect(
    page.getByText(
      /blockchain|Polygon|PayOS|SHA-256|Mạng ghi nhận|Chi tiết nâng cao|Mã toàn vẹn|0x[0-9a-f]{8}/i,
    ),
  ).toHaveCount(0);
  await expect(page.getByText("Đối chiếu tài liệu")).toHaveCount(0);
  await expect(page.getByLabel("Chọn tài liệu để đối chiếu")).toHaveCount(0);
});

test("certificate work action remains readable in light and dark themes", async ({
  page,
}) => {
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await page.goto("/verify/demo-token");
    const action = page
      .locator(".digital-certificate")
      .getByRole("link", { name: "Xem tác phẩm" });
    await expect(action).toBeVisible();
    await expect(action).toHaveAttribute("href", /\/works\//);
    expect(
      await action.evaluate(
        (element) => element.getBoundingClientRect().height,
      ),
    ).toBeGreaterThanOrEqual(44);
  }
});
