import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { DecisionDocumentViewer } from "./decision-document-viewer";
const getDocument = vi.hoisted(() => vi.fn());
vi.mock("pdfjs-dist", () => ({
  GlobalWorkerOptions: { workerSrc: "" },
  getDocument,
}));
afterEach(() => vi.unstubAllGlobals());
it("retains the original download/browser fallback if rendering cannot start", async () => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      disconnect() {}
    },
  );
  getDocument.mockImplementation(() => ({
    promise: Promise.reject(new Error("Unavailable")),
    destroy: vi.fn(),
  }));
  render(<DecisionDocumentViewer />);
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Chưa xem được văn bản",
  );
  expect(
    screen
      .getByRole("link", { name: "Mở bằng trình duyệt" })
      .getAttribute("href"),
  ).toBe("/assets/institution/decision.pdf");
  expect(
    screen.getByRole("link", { name: "Tải PDF gốc" }).hasAttribute("download"),
  ).toBe(true);
});
