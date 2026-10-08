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
    delete (window as Window & { __thvInstallPrompt?: Event })
      .__thvInstallPrompt;
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: vi.fn().mockReturnValue({ matches: false }),
    });
  });

  it("keeps the download CTA linked to installation when a native prompt is unavailable", () => {
    render(<PwaInstallButton />);
    expect(
      screen.getByRole("link", { name: "Tải ứng dụng" }).getAttribute("href"),
    ).toBe("/install");
  });

  it("opens the native install dialog from the header in one tap when ready", async () => {
    const user = userEvent.setup();
    const { event, prompt } = installPrompt();
    render(<PwaInstallButton />);

    fireEvent(window, event);
    await user.click(
      await screen.findByRole("button", { name: "Tải ứng dụng" }),
    );

    expect(prompt).toHaveBeenCalledOnce();
  });

  it("uses an install prompt captured before React mounted", async () => {
    const { event, prompt } = installPrompt();
    (window as Window & { __thvInstallPrompt?: Event }).__thvInstallPrompt =
      event;
    render(<PwaInstallButton />);

    await userEvent
      .setup()
      .click(await screen.findByRole("button", { name: "Tải ứng dụng" }));
    expect(prompt).toHaveBeenCalledOnce();
  });

  it("returns to the install guide if the native prompt fails", async () => {
    const user = userEvent.setup();
    const { event, prompt } = installPrompt();
    prompt.mockRejectedValueOnce(new Error("prompt unavailable"));
    render(<PwaInstallButton />);

    fireEvent(window, event);
    await user.click(
      await screen.findByRole("button", { name: "Tải ứng dụng" }),
    );

    expect(
      await screen.findByRole("link", { name: "Tải ứng dụng" }),
    ).toBeDefined();
  });

  it("starts native installation only from the guide action", async () => {
    const user = userEvent.setup();
    const { event, prompt } = installPrompt();
    render(<PwaInstallAction />);
    fireEvent(window, event);
    expect(prompt).not.toHaveBeenCalled();
    await user.click(
      await screen.findByRole("button", { name: "Tải ứng dụng" }),
    );
    expect(prompt).toHaveBeenCalledOnce();
    await waitFor(() =>
      expect(screen.getByRole("status").textContent).toContain(
        "Đã xác nhận cài đặt",
      ),
    );
  });

  it("keeps both the install action and manual guidance when no prompt is available", async () => {
    render(<PwaInstallAction />);
    expect(
      await screen.findByText(/Nếu trình duyệt chưa mở hộp thoại cài đặt/),
    ).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Xem cách cài trên thiết bị" })
        .getAttribute("href"),
    ).toBe("#install-device-steps");
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Tải ứng dụng" }));
    expect(screen.getByRole("status").textContent).toContain(
      "Chưa mở được hộp thoại cài đặt",
    );
  });

  it("shows iPhone steps immediately without promising an automatic prompt", async () => {
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1",
    );
    try {
      render(<PwaInstallAction />);
      expect(await screen.findByText(/Safari.*Chia sẻ/)).toBeDefined();
      expect(screen.queryByRole("button", { name: "Tải ứng dụng" })).toBeNull();
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
      expect(screen.queryByRole("link", { name: "Tải ứng dụng" })).toBeNull(),
    );
  });
});
