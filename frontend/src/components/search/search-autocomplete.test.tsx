import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SearchAutocomplete } from "@/components/search/search-autocomplete";
import { publicApi } from "@/lib/api/client";

const push = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api/client", () => ({
  publicApi: { autocomplete: vi.fn() },
}));

beforeEach(() => {
  vi.useFakeTimers();
  push.mockReset();
  vi.mocked(publicApi.autocomplete).mockResolvedValue([
    { kind: "work", label: "Sơn mài di sản", slug: "son-mai-di-san" },
    { kind: "category", label: "Sơn mài", slug: "son-mai" },
  ]);
});

afterEach(() => vi.useRealTimers());

describe("SearchAutocomplete", () => {
  it("debounces requests and ignores queries shorter than two characters", async () => {
    render(<SearchAutocomplete />);
    const input = screen.getByRole("combobox", { name: "Tìm đề cử" });

    fireEvent.change(input, { target: { value: "s" } });
    await act(() => vi.advanceTimersByTimeAsync(300));
    expect(publicApi.autocomplete).not.toHaveBeenCalled();

    fireEvent.change(input, { target: { value: "sơn" } });
    await act(() => vi.advanceTimersByTimeAsync(249));
    expect(publicApi.autocomplete).not.toHaveBeenCalled();
    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(publicApi.autocomplete).toHaveBeenCalledTimes(1);
  });

  it("exposes an ARIA listbox and supports keyboard selection", async () => {
    render(<SearchAutocomplete />);
    const input = screen.getByRole("combobox", { name: "Tìm đề cử" });

    fireEvent.change(input, { target: { value: "sơn" } });
    await act(() => vi.advanceTimersByTimeAsync(250));
    expect(screen.getByRole("listbox")).toBeTruthy();
    expect(input.getAttribute("aria-expanded")).toBe("true");

    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(push).toHaveBeenCalledWith("/works/son-mai-di-san");
  });
});
