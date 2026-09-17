import { render } from "@testing-library/react";
import { expect, it } from "vitest";

import { AdaptiveVideo } from "@/components/public/adaptive-video";

it("preloads metadata and the fallback video immediately", () => {
  const { container } = render(<AdaptiveVideo fallbackUrl="/video.mp4" />);
  const video = container.querySelector("video")!;

  expect(video.preload).toBe("metadata");
  expect(video.getAttribute("src")).toBe("/video.mp4");
});
