import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageLoading } from "@/components/ui/page-loading";

describe("PageLoading", () => {
  it("announces progress while keeping decorative placeholders hidden", () => {
    const { container } = render(<PageLoading />);

    expect(screen.getByRole("status").textContent).toContain(
      "Đang tải nội dung",
    );
    expect(
      container.querySelector('[aria-hidden="true"] .page-loading__shape'),
    ).not.toBeNull();
  });
});
