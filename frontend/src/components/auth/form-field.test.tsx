import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { FormField } from "@/components/auth/form-field";

describe("FormField", () => {
  it("lets people reveal and hide a password without changing its value", async () => {
    render(<FormField label="Mật khẩu" type="password" />);

    const input = screen.getByLabelText("Mật khẩu");
    await userEvent.type(input, "correct horse battery staple");

    const reveal = screen.getByRole("button", { name: "Hiện mật khẩu" });
    await userEvent.click(reveal);

    expect(input.getAttribute("type")).toBe("text");
    expect((input as HTMLInputElement).value).toBe(
      "correct horse battery staple",
    );
    expect(screen.getByRole("button", { name: "Ẩn mật khẩu" })).toBeDefined();
  });
});
