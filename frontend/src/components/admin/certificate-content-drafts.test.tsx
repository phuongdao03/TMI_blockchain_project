import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { CertificateContentDrafts } from "@/components/admin/certificate-content-drafts";
import { adminCertificateApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  adminCertificateApi: {
    contentDrafts: vi.fn(),
    updateContentDraft: vi.fn(),
    confirmContentDraft: vi.fn(),
  },
}));

it("edits, removes, previews, and confirms certificate content", async () => {
  const draft = {
    dossierId: "dossier-1",
    dossierCode: "THV-001",
    dossierTitle: "Đồng diễn múa Saravan",
    dossierStatus: "PAID",
    content: {
      title: "Đồng diễn múa Saravan",
      summary: "Mô tả cũ",
      subject: "Tác giả cũ",
      category: "Tài sản trí tuệ số",
    },
    confirmedAt: null,
  };
  let current = draft;
  vi.mocked(adminCertificateApi.contentDrafts).mockImplementation(async () => [
    current,
  ]);
  vi.mocked(adminCertificateApi.updateContentDraft).mockImplementation(
    async (_id, content) => {
      current = { ...draft, content };
      return current;
    },
  );
  vi.mocked(adminCertificateApi.confirmContentDraft).mockResolvedValue({
    ...draft,
    confirmedAt: "2026-10-06T00:00:00Z",
  });
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <CertificateContentDrafts />
    </QueryClientProvider>,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: /Đồng diễn múa Saravan/ }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Xóa tên người được ghi nhận" }),
  );
  expect(
    screen.getByLabelText("Xem trước nội dung bằng xác lập").textContent,
  ).not.toContain("Tác giả cũ");
  fireEvent.click(screen.getByRole("button", { name: "Lưu nội dung" }));
  await waitFor(() =>
    expect(adminCertificateApi.updateContentDraft).toHaveBeenCalledWith(
      "dossier-1",
      { ...draft.content, subject: "" },
    ),
  );
  await waitFor(() =>
    expect(
      screen
        .getByRole("button", { name: "Xác nhận phát hành" })
        .hasAttribute("disabled"),
    ).toBe(false),
  );
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận phát hành" }));
  await waitFor(() =>
    expect(
      vi.mocked(adminCertificateApi.confirmContentDraft).mock.calls[0]?.[0],
    ).toBe("dossier-1"),
  );
});
