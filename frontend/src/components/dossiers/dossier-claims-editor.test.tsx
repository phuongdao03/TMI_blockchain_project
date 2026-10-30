import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Link from "next/link";
import { beforeEach, expect, it, vi } from "vitest";

import { DossierClaimsEditor } from "@/components/dossiers/dossier-claims-editor";
import { ApiError } from "@/lib/api/client";

const saveClaims = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  dossierApi: { saveClaims },
}));
const props = {
  dossierId: "dossier-1",
  initialRevision: 0,
  criteria: [{ key: "origin", label: "Nguồn gốc" }],
  evidences: [
    {
      id: "evidence-1",
      dossierId: "dossier-1",
      dossierVersionId: null,
      mediaAssetId: "media-1",
      title: "Bản thảo",
      evidenceType: "PRIMARY",
      evidenceRole: "PRIMARY",
      accessScope: "PRIVATE" as const,
      description: null,
      issuedAt: null,
      displayOrder: 0,
      isPublic: false,
      mimeType: "application/pdf",
      bytes: 100,
      sha256: "a".repeat(64),
    },
  ],
  readOnly: false,
  onSaved: vi.fn(),
  onUnsavedChange: vi.fn(),
};

beforeEach(() => vi.clearAllMocks());

it("saves applicant statements with explicit criterion/evidence and acknowledged revision", async () => {
  const user = userEvent.setup();
  saveClaims.mockImplementation(async (_id, _revision, claims) => ({
    claims,
    claimsRevision: 1,
  }));
  render(<DossierClaimsEditor {...props} />);
  await user.click(screen.getByRole("button", { name: "Thêm nhận định" }));
  await user.type(
    screen.getByRole("textbox", { name: "Nội dung nhận định 1" }),
    "Bản thảo ghi lại quá trình sáng tác độc lập.",
  );
  await user.click(screen.getByRole("checkbox", { name: "Bản thảo" }));
  await user.click(screen.getByRole("button", { name: "Lưu nhận định" }));
  await waitFor(() =>
    expect(saveClaims).toHaveBeenCalledWith("dossier-1", 0, [
      expect.objectContaining({
        criterionKey: "origin",
        evidenceMediaIds: ["media-1"],
      }),
    ]),
  );
  expect(props.onSaved).toHaveBeenCalled();
  expect(screen.getByRole("status").textContent).toBe("Nhận định đã lưu");
});

it("retains edits after conflict and blocks navigation until save or discard", async () => {
  const user = userEvent.setup();
  saveClaims.mockRejectedValue(
    new ApiError("stale", "DOSSIER_INVALID_STATE", 409),
  );
  render(
    <>
      <Link href="/dossiers">Rời hồ sơ</Link>
      <DossierClaimsEditor {...props} />
    </>,
  );
  await user.click(screen.getByRole("button", { name: "Thêm nhận định" }));
  await user.type(
    screen.getByRole("textbox", { name: "Nội dung nhận định 1" }),
    "Nội dung chưa đồng bộ phải được giữ lại.",
  );
  await user.click(screen.getByRole("button", { name: "Lưu nhận định" }));
  await waitFor(() =>
    expect(screen.getByRole("alert").textContent).toContain("phiên khác"),
  );
  expect(
    screen.getByRole("textbox", { name: "Nội dung nhận định 1" }),
  ).toHaveProperty("value", "Nội dung chưa đồng bộ phải được giữ lại.");
  await user.click(screen.getByRole("link", { name: "Rời hồ sơ" }));
  expect(screen.getByRole("alert").textContent).toContain(
    "trước khi chuyển trang",
  );
  await user.click(
    screen.getByRole("button", { name: "Hủy thay đổi nhận định" }),
  );
  expect(screen.queryByRole("textbox")).toBeNull();
});

it("renders frozen claims without editable controls", () => {
  render(
    <DossierClaimsEditor
      {...props}
      readOnly
      initialClaims={[
        {
          id: "claim-1",
          criterionKey: "origin",
          statement: "Nhận định đã nộp",
          evidenceMediaIds: ["media-1"],
        },
      ]}
    />,
  );
  expect(
    screen
      .getByRole("textbox", { name: "Nội dung nhận định 1" })
      .closest("fieldset"),
  ).toHaveProperty("disabled", true);
  expect(screen.queryByRole("button", { name: "Lưu nhận định" })).toBeNull();
});
