import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ComingSoonFeature } from "./coming-soon-feature";

describe("ComingSoonFeature", () => {
  it("explains the unavailable feature and provides a working return action", () => {
    const { container } = render(<ComingSoonFeature feature="submission" />);

    expect(
      screen.getByRole("heading", { name: "Cổng gửi đề cử sẽ sớm ra mắt" }),
    ).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Khám phá các đề cử" })
        .getAttribute("href"),
    ).toBe("/works");
    expect(container.textContent).not.toMatch(/\bV1\b|Phiên bản/i);
  });
});
