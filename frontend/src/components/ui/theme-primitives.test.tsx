import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Bell } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Feedback } from "@/components/ui/feedback";
import { IconFrame } from "@/components/ui/icon-frame";

describe("theme-aware UI primitives", () => {
  it("uses semantic classes for buttons instead of fixed palette utilities", () => {
    render(<Button>Tiếp tục</Button>);

    expect(screen.getByRole("button").className).toContain("ui-button");
    expect(screen.getByRole("button").className).toContain(
      "ui-button--primary",
    );
  });

  it("keeps card typography tied to the active shell theme", () => {
    render(
      <Card>
        <CardTitle>Hồ sơ gần đây</CardTitle>
        <CardDescription>
          Tiếp tục công việc bạn đang thực hiện.
        </CardDescription>
      </Card>,
    );

    expect(screen.getByRole("heading").className).toContain("ui-card__title");
    expect(screen.getByText(/Tiếp tục công việc/).className).toContain(
      "ui-card__description",
    );
  });

  it("expresses feedback tone semantically for both themes", () => {
    render(<Feedback title="Đã lưu" tone="success" />);

    expect(screen.getByRole("status").className).toContain("ui-feedback");
    expect(screen.getByRole("status").className).toContain(
      "ui-feedback--success",
    );
  });

  it("gives decorative icons a consistent optical frame", () => {
    const { container } = render(<IconFrame icon={Bell} tone="brand" />);
    const frame = container.firstElementChild;

    expect(frame?.className).toContain("ui-icon-frame");
    expect(frame?.className).toContain("ui-icon-frame--brand");
    expect(frame?.querySelector("svg")?.getAttribute("aria-hidden")).toBe(
      "true",
    );
  });
});
