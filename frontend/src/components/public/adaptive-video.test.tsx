import { act, fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { AdaptiveVideo } from "@/components/public/adaptive-video";

it("keeps the video unloaded until the visitor chooses to play", () => {
  const { container } = render(<AdaptiveVideo fallbackUrl="/video.mp4" />);
  const video = container.querySelector("video")!;

  expect(video.preload).toBe("none");
  expect(video.getAttribute("src")).toBeNull();
});

it("warms a nearby video and reuses its buffer when playback starts", () => {
  const load = vi
    .spyOn(HTMLMediaElement.prototype, "load")
    .mockImplementation(() => {});
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  const observe = vi.fn();
  const disconnect = vi.fn();
  let notify: IntersectionObserverCallback = () => {};
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(callback: IntersectionObserverCallback) {
        notify = callback;
      }
      observe = observe;
      disconnect = disconnect;
    },
  );
  try {
    const { container } = render(<AdaptiveVideo fallbackUrl="/video.mp4" />);
    const video = container.querySelector("video")!;
    expect(observe).toHaveBeenCalledWith(video);
    expect(video.getAttribute("src")).toBeNull();

    act(() =>
      notify(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      ),
    );
    expect(video.getAttribute("src")).toBe("/video.mp4");
    expect(video.preload).toBe("metadata");
    expect(load).toHaveBeenCalledTimes(1);
    expect(disconnect).toHaveBeenCalled();

    fireEvent.click(
      screen.getByRole("button", { name: "Phát video tác phẩm" }),
    );
    expect(load).toHaveBeenCalledTimes(1);
    expect(play).toHaveBeenCalledTimes(1);
  } finally {
    load.mockRestore();
    play.mockRestore();
    vi.unstubAllGlobals();
  }
});

it("does not restart playback if the video enters view after a tap", () => {
  const load = vi
    .spyOn(HTMLMediaElement.prototype, "load")
    .mockImplementation(() => {});
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  let notify: IntersectionObserverCallback = () => {};
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(callback: IntersectionObserverCallback) {
        notify = callback;
      }
      observe = vi.fn();
      disconnect = vi.fn();
    },
  );
  try {
    const { container } = render(<AdaptiveVideo fallbackUrl="/video.mp4" />);
    const video = container.querySelector("video")!;
    fireEvent.click(
      screen.getByRole("button", { name: "Phát video tác phẩm" }),
    );
    act(() =>
      notify(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      ),
    );
    expect(video.getAttribute("src")).toBe("/video.mp4");
    expect(load).toHaveBeenCalledTimes(1);
    expect(play).toHaveBeenCalledTimes(1);
  } finally {
    load.mockRestore();
    play.mockRestore();
    vi.unstubAllGlobals();
  }
});

it("does not warm video when data saving is enabled", () => {
  const load = vi
    .spyOn(HTMLMediaElement.prototype, "load")
    .mockImplementation(() => {});
  const originalConnection = Object.getOwnPropertyDescriptor(
    navigator,
    "connection",
  );
  const observe = vi.fn();
  Object.defineProperty(navigator, "connection", {
    configurable: true,
    value: { saveData: true },
  });
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe = observe;
      disconnect = vi.fn();
    },
  );
  try {
    const { container } = render(<AdaptiveVideo fallbackUrl="/video.mp4" />);
    expect(container.querySelector("video")?.getAttribute("src")).toBeNull();
    expect(observe).not.toHaveBeenCalled();
    expect(load).not.toHaveBeenCalled();
  } finally {
    if (originalConnection)
      Object.defineProperty(navigator, "connection", originalConnection);
    else Reflect.deleteProperty(navigator, "connection");
    load.mockRestore();
    vi.unstubAllGlobals();
  }
});

it("starts the adaptive stream and falls back to MP4 on error", () => {
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
    expect(video.getAttribute("src")).toBe("/adaptive.m3u8");
    expect(video.preload).toBe("metadata");
    fireEvent.error(video);
    expect(video.getAttribute("src")).toBe("/optimized.mp4");
    expect(play).toHaveBeenCalled();
  } finally {
    load.mockRestore();
    play.mockRestore();
    canPlayType.mockRestore();
  }
});

it("does not warm the MP4 when adaptive streaming is available", () => {
  const load = vi
    .spyOn(HTMLMediaElement.prototype, "load")
    .mockImplementation(() => {});
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  const canPlayType = vi
    .spyOn(HTMLMediaElement.prototype, "canPlayType")
    .mockReturnValue("maybe");
  try {
    const observe = vi.fn();
    vi.stubGlobal(
      "IntersectionObserver",
      class {
        observe = observe;
        disconnect = vi.fn();
      },
    );
    const { container } = render(
      <AdaptiveVideo
        fallbackUrl="/optimized.mp4"
        streamingUrl="/adaptive.m3u8"
      />,
    );
    const video = container.querySelector("video")!;
    expect(observe).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole("button", { name: "Phát video tác phẩm" }),
    );
    expect(video.getAttribute("src")).toBe("/adaptive.m3u8");
    expect(load).toHaveBeenCalledTimes(1);
  } finally {
    load.mockRestore();
    play.mockRestore();
    canPlayType.mockRestore();
    vi.unstubAllGlobals();
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
    expect(
      container.querySelector(".adaptive-video__loading svg"),
    ).not.toBeNull();
    fireEvent.playing(video);
    expect(container.querySelector(".adaptive-video__loading")).toBeNull();
  } finally {
    load.mockRestore();
    play.mockRestore();
  }
});
