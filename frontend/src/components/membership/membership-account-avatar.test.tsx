import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MembershipAccountAvatar } from "./membership-account-avatar";

const api = vi.hoisted(() => ({ overview: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ membershipApi: api }));

function mount(user: {
  id: string;
  email: string;
  roles: string[];
  permissions?: string[];
  accountType: "PUBLIC_USER";
}) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MembershipAccountAvatar user={user} displayName="Lan Nguyen" size={32} />
    </QueryClientProvider>,
  );
}

describe("membership account avatar", () => {
  it("shows the actual matching rank frame in an outer account header", async () => {
    api.overview.mockResolvedValue({ tier: "SILVER" });
    const { container } = mount({
      id: "member-1",
      email: "member@example.vn",
      roles: ["USER"],
      accountType: "PUBLIC_USER",
    });

    await screen.findByRole("img", { name: "Ảnh đại diện của Lan Nguyen" });
    await waitFor(() => {
      const frames = [...container.querySelectorAll("img")];
      expect(
        frames.some((image) =>
          decodeURIComponent(image.src).includes("/avatar-frames/silver.png"),
        ),
      ).toBe(true);
    });
  });

  it.each([
    ["SUPER_ADMIN", ["SUPER_ADMIN"], []],
    ["membership manager", ["MODERATOR"], ["memberships.manage"]],
  ])(
    "does not query or display a personal rank for %s",
    async (_label, roles, permissions) => {
      api.overview.mockClear();
      const { container } = mount({
        id: "admin-1",
        email: "admin@example.vn",
        roles,
        permissions,
        accountType: "PUBLIC_USER",
      });

      expect(
        screen.getByRole("img", { name: "Ảnh đại diện của Lan Nguyen" }),
      ).toBeDefined();
      expect((container.firstElementChild as HTMLElement).style.boxShadow).toBe(
        "",
      );
      expect(container.querySelector('img[src*="avatar-frames"]')).toBeNull();
      expect(api.overview).not.toHaveBeenCalled();
    },
  );
});
