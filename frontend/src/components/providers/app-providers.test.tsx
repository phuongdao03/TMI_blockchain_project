import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "@/components/providers/app-providers";
import { authApi } from "@/lib/api/client";

let pathname = "/search";

vi.mock("next/navigation", () => ({ usePathname: () => pathname }));
vi.mock("@/lib/api/client", () => ({
  authApi: { currentUser: vi.fn() },
}));

beforeEach(() => {
  pathname = "/search";
  vi.mocked(authApi.currentUser).mockReset().mockResolvedValue(null);
});

describe("AppProviders", () => {
  it("leaves private session bootstrap to the dashboard auth guard", async () => {
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
    await waitFor(() => expect(screen.getByText("Dashboard")).toBeTruthy());
    expect(authApi.currentUser).not.toHaveBeenCalled();
  });

  it.each(["/process", "/policies", "/login", "/register"])(
    "does not request a session for %s",
    async (route) => {
      pathname = route;
      render(
        <AppProviders>
          <p>Public screen</p>
        </AppProviders>,
      );

      await Promise.resolve();
      expect(authApi.currentUser).not.toHaveBeenCalled();
    },
  );
});
