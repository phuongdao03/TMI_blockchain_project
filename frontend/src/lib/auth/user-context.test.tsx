import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authApi } from "@/lib/api/client";
import type { AuthUser } from "@/lib/api/types";
import {
  PublicAuthProvider,
  useAuthStatus,
  useAuthUser,
} from "@/lib/auth/user-context";
import { AUTH_SESSION_CHANGE_KEY } from "@/lib/auth/session-sync";

vi.mock("@/lib/api/client", () => ({
  authApi: { currentUser: vi.fn() },
}));

const user: AuthUser = {
  id: "applicant",
  email: "applicant@example.vn",
  roles: ["USER"],
  accountType: "INDIVIDUAL_APPLICANT",
};

function AccountStatus() {
  const status = useAuthStatus();
  const account = useAuthUser();
  return <output>{`${status}:${account?.id ?? "guest"}`}</output>;
}

function setup(initialUser: AuthUser | null, hasSessionCookie: boolean) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  function tree(account: AuthUser | null, cookie: boolean) {
    return (
      <QueryClientProvider client={client}>
        <PublicAuthProvider initialUser={account} hasSessionCookie={cookie}>
          <AccountStatus />
        </PublicAuthProvider>
      </QueryClientProvider>
    );
  }
  const view = render(tree(initialUser, hasSessionCookie));
  return {
    ...view,
    update: (account: AuthUser | null, cookie: boolean) =>
      view.rerender(tree(account, cookie)),
  };
}

describe("public session state", () => {
  afterEach(() => vi.resetAllMocks());

  it("resolves a cookie-free guest immediately without requesting a session", () => {
    setup(null, false);
    expect(screen.getByText("unauthenticated:guest")).toBeDefined();
    expect(authApi.currentUser).not.toHaveBeenCalled();
  });

  it("renders a server-authenticated account without a guest flash", () => {
    setup(user, true);
    expect(screen.getByText("authenticated:applicant")).toBeDefined();
  });

  it("recovers a refresh-cookie session before exposing guest actions", async () => {
    let finish!: (account: AuthUser | null) => void;
    vi.mocked(authApi.currentUser).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    setup(null, true);
    expect(screen.getByText("loading:guest")).toBeDefined();
    await act(async () => finish(user));
    await waitFor(() =>
      expect(screen.getByText("authenticated:applicant")).toBeDefined(),
    );
  });

  it("accepts a refreshed server account in a preserved public layout", async () => {
    const view = setup(null, false);
    view.update(user, true);
    await waitFor(() =>
      expect(screen.getByText("authenticated:applicant")).toBeDefined(),
    );
  });

  it("drops the old account when the server confirms logout", async () => {
    const view = setup(user, true);
    view.update(null, false);
    await waitFor(() =>
      expect(screen.getByText("unauthenticated:guest")).toBeDefined(),
    );
  });

  it("rechecks cross-tab logout and stops exposing the old identity", async () => {
    vi.mocked(authApi.currentUser).mockResolvedValue(null);
    setup(user, true);
    act(() =>
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: AUTH_SESSION_CHANGE_KEY,
        }),
      ),
    );
    await waitFor(() =>
      expect(screen.getByText("unauthenticated:guest")).toBeDefined(),
    );
  });

  it("does not label a network failure as a confirmed guest", async () => {
    vi.mocked(authApi.currentUser).mockRejectedValue(new Error("offline"));
    setup(null, true);
    await waitFor(() => expect(screen.getByText("error:guest")).toBeDefined());
  });

  it("uses the refreshed server identity after a prior client session check", async () => {
    vi.mocked(authApi.currentUser).mockResolvedValue(user);
    const view = setup(null, true);
    await waitFor(() =>
      expect(screen.getByText("authenticated:applicant")).toBeDefined(),
    );
    view.update({ ...user, id: "updated-account" }, true);
    await waitFor(() =>
      expect(screen.getByText("authenticated:updated-account")).toBeDefined(),
    );
  });

  it("clears a recovered account when the refreshed server has no cookies", async () => {
    vi.mocked(authApi.currentUser).mockResolvedValue(user);
    const view = setup(null, true);
    await waitFor(() =>
      expect(screen.getByText("authenticated:applicant")).toBeDefined(),
    );
    view.update(null, false);
    await waitFor(() =>
      expect(screen.getByText("unauthenticated:guest")).toBeDefined(),
    );
  });
});
