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
    expect(screen.getAllByText("TMI xử lý gì?")).toHaveLength(5);
    expect(screen.getAllByText("Bạn nhận được gì?")).toHaveLength(5);
    expect(container.textContent).not.toMatch(forbiddenPublicTerms);
  });

  it("documents every required policy section with keyboard anchors", () => {
    const { container } = render(<PolicyGuide />);

    expect(policySections).toHaveLength(7);
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
  });

  it("explains public, applicant and invited-staff entry points as tasks", () => {
    const { container } = render(<AccessGuide />);

    expect(screen.getByText("Tra cứu công khai")).toBeDefined();
    expect(screen.getByText("Gửi hồ sơ")).toBeDefined();
    expect(screen.getByText("Làm việc nội bộ")).toBeDefined();
    expect(container.textContent).not.toMatch(forbiddenPublicTerms);
  });
});
