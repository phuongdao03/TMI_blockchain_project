import { act, fireEvent, render, screen } from "@testing-library/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { afterEach, expect, it, vi } from "vitest";

import { NavigationLoading } from "@/components/ui/navigation-loading";

vi.mock("next/navigation", () => ({ usePathname: vi.fn(() => "/") }));

afterEach(() => {
  vi.useRealTimers();
});

it("shows navigation feedback after a mobile link tap and clears on arrival", () => {
  vi.useFakeTimers();
  const { rerender } = render(
    <>
      <NavigationLoading />
      <Link href="/certificates" onClick={(event) => event.preventDefault()}>
        Bằng xác lập
      </Link>
    </>,
  );
  fireEvent.click(screen.getByRole("link", { name: "Bằng xác lập" }));
  expect(screen.queryByRole("status")).toBeNull();
  act(() => vi.advanceTimersByTime(120));
  expect(screen.getByRole("status").textContent).toContain("Đang mở trang");
  vi.mocked(usePathname).mockReturnValue("/certificates");
  rerender(
    <>
      <NavigationLoading />
      <Link href="/certificates" onClick={(event) => event.preventDefault()}>
        Bằng xác lập
      </Link>
    </>,
  );
  expect(screen.queryByRole("status")).toBeNull();
});
