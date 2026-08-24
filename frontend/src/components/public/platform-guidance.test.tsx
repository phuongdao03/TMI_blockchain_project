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
  it("presents four concise public milestones with the action and outcome at each step", () => {
    const { container } = render(<ProcessGuide />);

    expect(screen.getAllByText("Bạn thực hiện")).toHaveLength(4);
    expect(screen.getAllByText("Kết quả bạn nhận")).toHaveLength(4);
    expect(screen.getByText("Tạo và hoàn thiện hồ sơ")).toBeDefined();
    expect(screen.getByText("Nộp để kiểm tra")).toBeDefined();
    expect(screen.getByText("Thẩm định & phản hồi")).toBeDefined();
    expect(screen.getByText("Xác lập và công bố")).toBeDefined();
    expect(container.textContent).not.toMatch(forbiddenPublicTerms);
    expect(container.textContent).not.toMatch(
      /loại tài khoản|tài khoản nội bộ/i,
    );
  });

  it("documents production-ready terms and privacy sections with keyboard anchors", () => {
    const { container } = render(<PolicyGuide />);

    expect(policySections).toHaveLength(6);
    expect(policySections.map((section) => section.title)).toEqual([
      "Điều khoản sử dụng",
      "Tài khoản và hồ sơ",
      "Chính sách quyền riêng tư",
      "Công bố, kiểm chứng và chứng thư",
      "Quyền, nghĩa vụ và giới hạn trách nhiệm",
      "Cập nhật chính sách",
    ]);
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
    expect(screen.getByText("Gửi và theo dõi hồ sơ")).toBeDefined();
    expect(screen.getByText("Cần tài khoản")).toBeDefined();
    expect(screen.queryByText("Làm việc nội bộ")).toBeNull();
    expect(container.textContent).not.toMatch(forbiddenPublicTerms);
    expect(container.textContent).not.toMatch(
      /cá nhân và tổ chức|loại tài khoản/i,
    );
  });
});
