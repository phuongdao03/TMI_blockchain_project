import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "@/components/providers/app-providers";
import { authApi } from "@/lib/api/client";

let pathname = "/tim-kiem";

vi.mock("next/navigation", () => ({ usePathname: () => pathname }));
vi.mock("@/lib/api/client", () => ({
  authApi: { currentUser: vi.fn() },
}));

beforeEach(() => {
  pathname = "/tim-kiem";
  vi.mocked(authApi.currentUser).mockReset().mockResolvedValue(null);
});

describe("AppProviders", () => {
  it("does not bootstrap a private session on the public search route", async () => {
    const view = render(
      <AppProviders>
        <p>Public search</p>
      </AppProviders>,
    );
    expect(screen.getByText("Public search")).toBeTruthy();
    await Promise.resolve();
    expect(authApi.currentUser).not.toHaveBeenCalled();

    pathname = "/dashboard";
    view.rerender(
      <AppProviders>
        <p>Dashboard</p>
      </AppProviders>,
    );
    await waitFor(() => expect(authApi.currentUser).toHaveBeenCalledTimes(1));
  });
});
