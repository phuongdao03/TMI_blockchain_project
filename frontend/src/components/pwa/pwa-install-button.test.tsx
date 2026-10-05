import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  PwaInstallAction,
  PwaInstallButton,
} from "@/components/pwa/pwa-install-button";

function installPrompt(outcome: "accepted" | "dismissed" = "accepted") {
  const event = new Event("beforeinstallprompt", { cancelable: true });
  const prompt = vi.fn().mockResolvedValue(undefined);
  Object.assign(event, {
    prompt,
    userChoice: Promise.resolve({ outcome, platform: "web" }),
  });
  return { event, prompt };
}

describe("PWA installation", () => {
  beforeEach(() => {
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: vi.fn().mockReturnValue({ matches: false }),
    });
  });

  it("takes the header CTA to the installation guide", () => {
    render(<PwaInstallButton />);
    expect(
      screen
        .getByRole("link", { name: "Xem hướng dẫn cài ứng dụng" })
        .getAttribute("href"),
    ).toBe("/install");
  });

  it("starts native installation only from the guide action", async () => {
    const user = userEvent.setup();
    const { event, prompt } = installPrompt();
    render(
      <>
        <PwaInstallButton />
        <PwaInstallAction />
      </>,
    );
    fireEvent(window, event);
    expect(prompt).not.toHaveBeenCalled();
    await user.click(
      await screen.findByRole("button", { name: "Tiến hành cài đặt" }),
    );
    expect(prompt).toHaveBeenCalledOnce();
    await waitFor(() =>
      expect(screen.getByRole("status").textContent).toContain(
        "Đã xác nhận cài đặt",
      ),
    );
  });

  it("shows manual guidance when a native prompt is unavailable", async () => {
    render(<PwaInstallAction />);
    expect(
      await screen.findByText(/Trình duyệt chưa cung cấp hộp thoại/),
    ).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Xem cách cài trên thiết bị" })
        .getAttribute("href"),
    ).toBe("#install-device-steps");
    expect(
      screen.queryByRole("button", { name: "Tiến hành cài đặt" }),
    ).toBeNull();
  });

  it("shows iPhone steps immediately without promising an automatic prompt", async () => {
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1",
    );
    try {
      render(<PwaInstallAction />);
      expect(await screen.findByText(/Safari.*Chia sẻ/)).toBeDefined();
      expect(
        screen.queryByRole("button", { name: "Tiến hành cài đặt" }),
      ).toBeNull();
      expect(
        screen
          .getByRole("link", { name: /Xem các bước trên iPhone/ })
          .getAttribute("href"),
      ).toBe("#install-device-steps");
    } finally {
      vi.restoreAllMocks();
    }
  });

  it("hides the CTA inside the installed application", async () => {
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: vi.fn().mockReturnValue({ matches: true }),
    });
    render(<PwaInstallButton />);
    await waitFor(() =>
      expect(
        screen.queryByRole("link", { name: "Xem hướng dẫn cài ứng dụng" }),
      ).toBeNull(),
    );
  });
});
