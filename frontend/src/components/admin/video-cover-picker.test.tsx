import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VideoCoverPicker } from "@/components/admin/video-cover-picker";
import { publicWorkAdminApi } from "@/lib/api/client";
import type { PublicWorkMedia } from "@/lib/api/types";

vi.mock("@/lib/api/client", () => ({
  publicWorkAdminApi: { configureVideo: vi.fn().mockResolvedValue({}) },
}));
const item: PublicWorkMedia = {
  id: "relation",
  mediaAssetId: "asset",
  mediaKind: "VIDEO",
  sortOrder: 0,
  caption: null,
  altText: null,
  derivativeStatus: "READY",
  derivativeMimeType: "video/mp4",
  derivativeWidth: 1280,
  derivativeHeight: 720,
  durationMs: 100000,
  attemptCount: 0,
  failureCode: null,
  posterMediaAssetId: null,
  posterTimeMs: null,
  videoControlsPreset: "FULL",
  videoFitMode: "CONTAIN",
  videoQualityProfile: "BALANCED",
  videoMaxWidth: 1280,
  videoAutoplay: false,
  videoLoop: false,
  videoMuted: false,
};

describe("VideoCoverPicker", () => {
  it("offers later frames and persists a custom time without uploading again", async () => {
    const changed = vi.fn();
    render(
      <VideoCoverPicker
        item={item}
        workId="work"
        posterUrl="/poster.jpg"
        onChanged={changed}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Chọn khung tại 50 giây" }),
    );
    expect(screen.getByAltText("Ảnh bìa đã chọn").getAttribute("src")).toMatch(
      /posterTimeMs=50000$/,
    );
    fireEvent.change(screen.getByLabelText("Thời điểm lấy bìa (giây)"), {
      target: { value: "12.5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Xem khung hình" }));
    expect(
      screen
        .getByRole("button", { name: "Lưu khung hình làm bìa" })
        .hasAttribute("disabled"),
    ).toBe(true);
    fireEvent.load(screen.getByAltText("Ảnh bìa đã chọn"));
    await waitFor(() =>
      expect(
        screen
          .getByRole("button", { name: "Lưu khung hình làm bìa" })
          .hasAttribute("disabled"),
      ).toBe(false),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Lưu khung hình làm bìa" }),
    );
    await waitFor(() =>
      expect(publicWorkAdminApi.configureVideo).toHaveBeenCalledWith(
        "work",
        "relation",
        expect.objectContaining({
          posterTimeMs: 12500,
          posterMediaAssetId: null,
        }),
      ),
    );
    expect(changed).toHaveBeenCalled();
  });
  it("rejects a time beyond the duration before requesting a frame", () => {
    render(
      <VideoCoverPicker
        item={item}
        workId="work"
        posterUrl="/poster.jpg"
        onChanged={() => {}}
      />,
    );
    fireEvent.change(screen.getByLabelText("Thời điểm lấy bìa (giây)"), {
      target: { value: "101" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Xem khung hình" }));
    expect(screen.getByRole("alert").textContent).toMatch(/nằm trong/);
    expect(screen.getByAltText("Ảnh bìa đã chọn").getAttribute("src")).toMatch(
      /poster.jpg$/,
    );
  });
});
