import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Feedback } from "@/components/ui/feedback";
import { ProcessStep } from "@/components/ui/process-step";
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeader,
  DataTableRow,
} from "@/components/ui/table";

describe("information primitives", () => {
  it("announces recoverable errors without relying on color", () => {
    render(
      <Feedback title="Không thể tải hồ sơ" tone="error">
        Thử tải lại sau ít phút.
      </Feedback>,
    );

    expect(screen.getByRole("alert").textContent).toContain(
      "Không thể tải hồ sơ",
    );
  });

  it("provides a caption and column headers for data tables", () => {
    render(
      <DataTable caption="Hồ sơ đang xử lý">
        <DataTableHeader>
          <DataTableRow>
            <DataTableHead>Mã hồ sơ</DataTableHead>
          </DataTableRow>
        </DataTableHeader>
        <DataTableBody>
          <DataTableRow>
            <DataTableCell>TMI-1024</DataTableCell>
          </DataTableRow>
        </DataTableBody>
      </DataTable>,
    );

    expect(screen.getByText("Hồ sơ đang xử lý").tagName).toBe("CAPTION");
    expect(screen.getByRole("columnheader").textContent).toBe("Mã hồ sơ");
  });

  it("keeps process steps in semantic heading order", () => {
    render(
      <ProcessStep number="01" title="Chuẩn bị hồ sơ">
        Tập hợp thông tin và tài liệu cần thiết.
      </ProcessStep>,
    );

    expect(
      screen.getByRole("heading", { level: 3, name: "Chuẩn bị hồ sơ" }),
    ).toBeDefined();
  });
});
