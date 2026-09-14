import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import InstallPage from "@/app/(public)/install/page";

vi.mock("@/components/pwa/pwa-install-button", () => ({ PwaInstallAction: () => <button>Tiến hành cài đặt</button> }));

describe("InstallPage", () => {
  it("explains installation before exposing the install action", () => {
    render(<InstallPage />);
    expect(screen.getByRole("heading", { level: 1, name: "Cài đặt trong vài bước" })).toBeDefined();
    expect(screen.getByText("iPhone hoặc iPad")).toBeDefined();
    expect(screen.getByText("Điện thoại Android")).toBeDefined();
    expect(screen.getByRole("button", { name: "Tiến hành cài đặt" })).toBeDefined();
  });
});
