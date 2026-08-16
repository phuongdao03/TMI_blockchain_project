import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ComingSoonFeature } from "./coming-soon-feature";

describe("ComingSoonFeature", () => {
  it("explains the unavailable feature and provides a working return action", () => {
    const { container } = render(<ComingSoonFeature feature="voting" />);

    expect(
      screen.getByRole("heading", { name: "Bình chọn sẽ sớm ra mắt" }),
    ).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Khám phá các đề cử" })
        .getAttribute("href"),
    ).toBe("/works");
    expect(container.textContent).not.toMatch(/\bV1\b|Phiên bản/i);
  });
});
