import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { AdaptiveVideo } from "@/components/public/adaptive-video";

it("keeps the video unloaded until the visitor chooses to play", () => {
  const { container } = render(<AdaptiveVideo fallbackUrl="/video.mp4" />);
  const video = container.querySelector("video")!;

  expect(video.preload).toBe("none");
  expect(video.getAttribute("src")).toBeNull();
});

it("starts the optimized video after a tap and falls back to HLS on error", () => {
  const load = vi
    .spyOn(HTMLMediaElement.prototype, "load")
    .mockImplementation(() => {});
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  const canPlayType = vi
    .spyOn(HTMLMediaElement.prototype, "canPlayType")
    .mockReturnValue("maybe");
  try {
    const { container } = render(
      <AdaptiveVideo
        fallbackUrl="/optimized.mp4"
        streamingUrl="/adaptive.m3u8"
      />,
    );
    const video = container.querySelector("video")!;
    fireEvent.click(
      screen.getByRole("button", { name: "Phát video tác phẩm" }),
    );
    expect(video.getAttribute("src")).toBe("/optimized.mp4");
    expect(video.preload).toBe("metadata");
    expect(play).toHaveBeenCalled();
    fireEvent.error(video);
    expect(video.getAttribute("src")).toBe("/adaptive.m3u8");
  } finally {
    load.mockRestore();
    play.mockRestore();
    canPlayType.mockRestore();
  }
});

it("switches to adaptive streaming when the initial video stalls", () => {
  const load = vi
    .spyOn(HTMLMediaElement.prototype, "load")
    .mockImplementation(() => {});
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  const canPlayType = vi
    .spyOn(HTMLMediaElement.prototype, "canPlayType")
    .mockReturnValue("maybe");
  try {
    const { container } = render(
      <AdaptiveVideo
        fallbackUrl="/optimized.mp4"
        streamingUrl="/adaptive.m3u8"
      />,
    );
    const video = container.querySelector("video")!;
    fireEvent.click(
      screen.getByRole("button", { name: "Phát video tác phẩm" }),
    );
    fireEvent.stalled(video);
    expect(video.getAttribute("src")).toBe("/adaptive.m3u8");
  } finally {
    load.mockRestore();
    play.mockRestore();
    canPlayType.mockRestore();
  }
});

it("keeps waiting for a slow video when no streaming alternative exists", () => {
  vi.useFakeTimers();
  const load = vi
    .spyOn(HTMLMediaElement.prototype, "load")
    .mockImplementation(() => {});
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  try {
    render(<AdaptiveVideo fallbackUrl="/large-video.mp4" />);
    fireEvent.click(
      screen.getByRole("button", { name: "Phát video tác phẩm" }),
    );
    vi.advanceTimersByTime(7_000);
    expect(screen.queryByText(/Video chưa phát được/)).toBeNull();
    expect(screen.getByText(/Đang tải video/)).toBeDefined();
  } finally {
    load.mockRestore();
    play.mockRestore();
    vi.useRealTimers();
  }
});

it("shows buffering feedback while playback waits for more data", () => {
  const load = vi
    .spyOn(HTMLMediaElement.prototype, "load")
    .mockImplementation(() => {});
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  try {
    const { container } = render(<AdaptiveVideo fallbackUrl="/video.mp4" />);
    const video = container.querySelector("video")!;
    fireEvent.click(
      screen.getByRole("button", { name: "Phát video tác phẩm" }),
    );
    fireEvent.playing(video);
    expect(screen.queryByText(/Đang tải video/)).toBeNull();
    fireEvent.waiting(video);
    expect(screen.getByText(/Đang tải video/)).toBeDefined();
  } finally {
    load.mockRestore();
    play.mockRestore();
  }
});
