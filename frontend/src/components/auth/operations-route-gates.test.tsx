import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import CouncilLayout from "@/app/(dashboard)/council/layout";
import ReviewsLayout from "@/app/(dashboard)/reviews/layout";
import { AuthUserProvider } from "@/lib/auth/user-context";

function userWith(roles: string[]) {
  return {
    id: "user-1",
    email: "user@tmigroup.vn",
    roles,
    accountType: "PUBLIC_USER" as const,
  };
}

describe("operations route gates", () => {
  it("blocks a public account from direct reviewer navigation", () => {
    render(
      <AuthUserProvider user={userWith(["PUBLIC_USER"])}>
        <ReviewsLayout>
          <p>Reviewer private content</p>
        </ReviewsLayout>
      </AuthUserProvider>,
    );

    expect(screen.queryByText("Reviewer private content")).toBeNull();
    expect(
      screen.getByRole("heading", {
        name: "Trang này chưa mở cho tài khoản của bạn",
      }),
    ).toBeDefined();
  });

  it("opens each work queue only for an assigned internal account", () => {
    const { rerender } = render(
      <AuthUserProvider user={userWith(["MODERATOR"])}>
        <ReviewsLayout>
          <p>Review queue</p>
        </ReviewsLayout>
      </AuthUserProvider>,
    );
    expect(screen.getByText("Review queue")).toBeDefined();

    rerender(
      <AuthUserProvider user={userWith(["MODERATOR"])}>
        <CouncilLayout>
          <p>Council queue</p>
        </CouncilLayout>
      </AuthUserProvider>,
    );
    expect(screen.getByText("Council queue")).toBeDefined();
  });
});
