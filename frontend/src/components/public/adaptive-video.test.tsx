import { act, render } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { AdaptiveVideo } from "@/components/public/adaptive-video";

it("prepares metadata near the viewport and does not reload when scrolling away", () => {
  let notify: IntersectionObserverCallback = () => {};
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(callback: IntersectionObserverCallback) {
        notify = callback;
      }
      observe() {}
      disconnect() {}
    },
  );
  try {
    const { container } = render(<AdaptiveVideo fallbackUrl="/video.mp4" />);
    const video = container.querySelector("video")!;
    expect(video.preload).toBe("none");
    const entry = { isIntersecting: true } as IntersectionObserverEntry;
    act(() => notify([entry], {} as IntersectionObserver));
    expect(video.preload).toBe("metadata");
    expect(video.getAttribute("src")).toBe("/video.mp4");
    act(() =>
      notify([{ ...entry, isIntersecting: false }], {} as IntersectionObserver),
    );
    expect(video.preload).toBe("metadata");
    expect(video.getAttribute("src")).toBe("/video.mp4");
  } finally {
    vi.unstubAllGlobals();
  }
});
