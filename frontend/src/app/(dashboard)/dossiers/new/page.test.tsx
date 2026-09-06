import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import CreateDossierPage from "@/app/(dashboard)/dossiers/new/page";

vi.mock("@/components/auth/role-gate", () => ({
  RoleGate: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("@/components/dossiers/dossier-create-form", () => ({
  DossierCreateForm: () => <div>Biểu mẫu hồ sơ</div>,
}));

describe("CreateDossierPage", () => {
  it("keeps the back link and page context visually separated", () => {
    render(<CreateDossierPage />);

    const backLink = screen.getByRole("link", { name: "Danh sách hồ sơ" });
    const context = screen.getByText("Hồ sơ mới");
    const navigationRow = backLink.parentElement;

    expect(navigationRow).toBe(context.parentElement);
    expect(navigationRow?.className).toContain("gap-3");
  });
});
