import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ThemeToggle } from "@/components/theme/theme-toggle";

describe("ThemeToggle", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.dataset.theme = "light";
    document.documentElement.dataset.themePreference = "system";
    vi.stubGlobal(
      "matchMedia",
      vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    );
  });

  it("presents an accessible segmented control instead of a native select", () => {
    render(<ThemeToggle />);

    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.getByRole("group", { name: "Chọn giao diện" })).toBeDefined();
    expect(
      screen
        .getByRole("button", { name: "Theo thiết bị" })
        .getAttribute("aria-pressed"),
    ).toBe("true");
    expect(
      screen.getByRole("button", { name: "Giao diện sáng" }),
    ).toBeDefined();
    expect(screen.getByRole("button", { name: "Giao diện tối" })).toBeDefined();
  });

  it("stores and applies an explicit theme", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);

    await user.click(screen.getByRole("button", { name: "Giao diện tối" }));

    expect(localStorage.getItem("thv-theme")).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(document.documentElement.dataset.themePreference).toBe("dark");
    expect(
      screen
        .getByRole("button", { name: "Giao diện tối" })
        .getAttribute("aria-pressed"),
    ).toBe("true");
  });

  it("uses the device preference when system is selected", async () => {
    vi.mocked(window.matchMedia).mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } as unknown as MediaQueryList);
    localStorage.setItem("thv-theme", "light");
    const user = userEvent.setup();
    render(<ThemeToggle />);

    await user.click(screen.getByRole("button", { name: "Theo thiết bị" }));

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem("thv-theme")).toBe("system");
  });

  it("keeps multiple theme controls synchronized", async () => {
    const user = userEvent.setup();
    render(
      <>
        <ThemeToggle />
        <ThemeToggle />
      </>,
    );

    await user.click(
      screen.getAllByRole("button", { name: "Giao diện tối" })[0]!,
    );

    expect(
      screen
        .getAllByRole("button", { name: "Giao diện tối" })[1]!
        .getAttribute("aria-pressed"),
    ).toBe("true");
  });
});
