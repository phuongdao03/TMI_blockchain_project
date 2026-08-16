import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  AccessGuide,
  PolicyGuide,
  policySections,
  ProcessGuide,
} from "@/components/public/platform-guidance";

const forbiddenPublicTerms =
  /\b(?:ADMIN|REVIEWER|COUNCIL|database|schema|backend|API|endpoint|CSRF|audit trail|workspace)\b/i;

describe("platform guidance", () => {
  it("answers the same three user questions for every process step", () => {
    const { container } = render(<ProcessGuide />);

    expect(screen.getAllByText("Bạn cần làm gì?")).toHaveLength(5);
    expect(screen.getAllByText("Điều gì diễn ra tiếp theo?")).toHaveLength(5);
    expect(screen.getAllByText("Bạn nhận được gì?")).toHaveLength(5);
    expect(screen.getByText("Khám phá chương trình")).toBeDefined();
    expect(screen.getByText("Chuẩn bị đề cử")).toBeDefined();
    expect(screen.getByText("Gửi đề cử")).toBeDefined();
    expect(container.textContent).not.toMatch(forbiddenPublicTerms);
    expect(container.textContent).not.toMatch(
      /loại tài khoản|tài khoản nội bộ/i,
    );
  });

  it("documents every required policy section with keyboard anchors", () => {
    const { container } = render(<PolicyGuide />);

    expect(policySections).toHaveLength(6);
    for (const section of policySections) {
      expect(
        screen.getByRole("heading", { name: section.title, level: 2 }),
      ).toBeDefined();
      expect(
        screen
          .getByRole("link", {
            name: new RegExp(section.title),
          })
          .getAttribute("href"),
      ).toBe(`#${section.id}`);
    }
    expect(container.textContent).not.toMatch(forbiddenPublicTerms);
    expect(container.textContent).not.toMatch(
      /tài khoản nhân sự|lời mời nội bộ/i,
    );
  });

  it("presents public actions without exposing account taxonomy", () => {
    const { container } = render(<AccessGuide />);

    expect(screen.getByText("Tra cứu công khai")).toBeDefined();
    expect(screen.getByText("Chuẩn bị gửi đề cử")).toBeDefined();
    expect(screen.getByText("Sắp ra mắt")).toBeDefined();
    expect(screen.queryByText("Làm việc nội bộ")).toBeNull();
    expect(container.textContent).not.toMatch(forbiddenPublicTerms);
    expect(container.textContent).not.toMatch(
      /cá nhân và tổ chức|loại tài khoản/i,
    );
  });
});
