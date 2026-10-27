import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { DossierPromotionOptions } from "./dossier-promotion-options";

it("offers ordinary publication tracking independently of optional advertising", () => {
  render(<DossierPromotionOptions dossierId="approved-id" status="PAID" />);
  expect(
    screen
      .getByRole("link", { name: "Theo dõi công bố thông thường" })
      .getAttribute("href"),
  ).toBe("#dossier-publication-progress");
  expect(
    screen
      .getByRole("link", { name: "Chọn gói quảng bá" })
      .getAttribute("href"),
  ).toBe("/advertising?dossierId=approved-id");
  expect(
    screen.getByText(/Quảng cáo không phải điều kiện công bố/),
  ).toBeDefined();
});
it("offers promotion after publication without a new submission", () => {
  render(
    <DossierPromotionOptions dossierId="published-id" status="PUBLISHED" />,
  );
  expect(
    screen
      .getByRole("link", { name: "Quảng bá hồ sơ này" })
      .getAttribute("href"),
  ).toBe("/advertising?dossierId=published-id");
  expect(screen.getByText(/không cần nộp lại hồ sơ/)).toBeDefined();
});
it("does not offer promotion on a rejected dossier", () => {
  const { container } = render(
    <DossierPromotionOptions dossierId="rejected" status="REJECTED" />,
  );
  expect(container.textContent).toBe("");
});
