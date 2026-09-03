import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DateControl, SelectControl } from "@/components/ui/form-controls";

describe("form controls", () => {
  it("keeps native mobile picker semantics with consistent accessible controls", () => {
    render(
      <>
        <label htmlFor="status">Trạng thái</label>
        <SelectControl id="status">
          <option value="active">Đang hoạt động</option>
        </SelectControl>
        <label htmlFor="from-date">Từ ngày</label>
        <DateControl id="from-date" />
      </>,
    );

    const select = screen.getByLabelText("Trạng thái");
    const date = screen.getByLabelText("Từ ngày");
    expect(select.tagName).toBe("SELECT");
    expect(select.className).toContain("ui-select-control");
    expect(date.getAttribute("type")).toBe("date");
    expect(date.className).toContain("ui-date-control");
  });
});
