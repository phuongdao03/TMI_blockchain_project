import { act, fireEvent, render, screen } from "@testing-library/react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { afterEach, expect, it, vi } from "vitest";

import { NavigationLoading } from "@/components/ui/navigation-loading";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/"),
  useSearchParams: vi.fn(() => new URLSearchParams()),
}));

afterEach(() => {
  vi.useRealTimers();
  vi.mocked(usePathname).mockReturnValue("/");
  vi.mocked(useSearchParams).mockReturnValue(
    new URLSearchParams() as ReturnType<typeof useSearchParams>,
  );
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
  expect(document.documentElement.dataset.navigationPending).toBe("true");
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
  expect(document.documentElement.dataset.navigationPending).toBeUndefined();
});

it("shows progress for a search form and clears when its query arrives", () => {
  vi.useFakeTimers();
  vi.mocked(usePathname).mockReturnValue("/works");
  const { rerender } = render(
    <>
      <NavigationLoading />
      <form action="/works" method="get">
        <input name="query" defaultValue="di sản" />
        <button type="submit">Tìm kiếm</button>
      </form>
    </>,
  );
  fireEvent.submit(
    screen.getByRole("button", { name: "Tìm kiếm" }).closest("form")!,
  );
  act(() => vi.advanceTimersByTime(120));
  expect(screen.getByRole("status").textContent).toContain("Đang mở trang");

  vi.mocked(useSearchParams).mockReturnValue(
    new URLSearchParams("query=di+s%E1%BA%A3n") as ReturnType<
      typeof useSearchParams
    >,
  );
  rerender(
    <>
      <NavigationLoading />
      <form action="/works" method="get">
        <input name="query" defaultValue="di sản" />
        <button type="submit">Tìm kiếm</button>
      </form>
    </>,
  );
  expect(screen.queryByRole("status")).toBeNull();
});

it("does not show navigation progress for an in-place form", () => {
  vi.useFakeTimers();
  render(
    <>
      <NavigationLoading />
      <form onSubmit={(event) => event.preventDefault()}>
        <button type="submit">Lưu tại chỗ</button>
      </form>
    </>,
  );
  fireEvent.submit(
    screen.getByRole("button", { name: "Lưu tại chỗ" }).closest("form")!,
  );
  act(() => vi.advanceTimersByTime(120));
  expect(screen.queryByRole("status")).toBeNull();
});
