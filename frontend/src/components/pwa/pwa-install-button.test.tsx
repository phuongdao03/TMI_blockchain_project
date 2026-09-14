import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PwaInstallAction, PwaInstallButton } from "@/components/pwa/pwa-install-button";

function installPrompt(outcome: "accepted" | "dismissed" = "accepted") {
  const event = new Event("beforeinstallprompt", { cancelable: true });
  const prompt = vi.fn().mockResolvedValue(undefined);
  Object.assign(event, { prompt, userChoice: Promise.resolve({ outcome, platform: "web" }) });
  return { event, prompt };
}

describe("PWA installation", () => {
  beforeEach(() => {
    Object.defineProperty(window, "matchMedia", { configurable: true, value: vi.fn().mockReturnValue({ matches: false }) });
  });

  it("takes the header CTA to the installation guide", () => {
    render(<PwaInstallButton />);
    expect(screen.getByRole("link", { name: "Xem hướng dẫn cài ứng dụng" }).getAttribute("href")).toBe("/install");
  });

  it("starts native installation only from the guide action", async () => {
    const user = userEvent.setup();
    const { event, prompt } = installPrompt();
    render(<><PwaInstallButton /><PwaInstallAction /></>);
    fireEvent(window, event);
    expect(prompt).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Tiến hành cài đặt" }));
    expect(prompt).toHaveBeenCalledOnce();
    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("đã được cài đặt"));
  });

  it("shows manual guidance when a native prompt is unavailable", async () => {
    const user = userEvent.setup();
    render(<PwaInstallAction />);
    await user.click(screen.getByRole("button", { name: "Tiến hành cài đặt" }));
    expect(screen.getByRole("status").textContent).toMatch(/Thêm vào màn hình chính/);
  });

  it("hides the CTA inside the installed application", async () => {
    Object.defineProperty(window, "matchMedia", { configurable: true, value: vi.fn().mockReturnValue({ matches: true }) });
    render(<PwaInstallButton />);
    await waitFor(() => expect(screen.queryByRole("link", { name: "Xem hướng dẫn cài ứng dụng" })).toBeNull());
  });
});
