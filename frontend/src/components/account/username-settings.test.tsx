import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { UsernameSettings } from "./username-settings";

const api = vi.hoisted(() => ({
  currentProfile: vi.fn(),
  updateProfile: vi.fn(),
}));
vi.mock("@/lib/api/client", () => ({ communityMemberApi: api }));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => ({ id: "owner" }),
}));
beforeEach(() => {
  vi.clearAllMocks();
  api.currentProfile.mockResolvedValue({ username: "old_name" });
});
it("saves a normalized username and explains its login purpose", async () => {
  api.updateProfile.mockResolvedValue({ username: "lan_anh" });
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <UsernameSettings />
    </QueryClientProvider>,
  );
  const input = await screen.findByLabelText("Username");
  await userEvent.clear(input);
  await userEvent.type(input, "Lan_Anh");
  await userEvent.click(
    screen.getByRole("button", { name: "Lưu tên đăng nhập" }),
  );
  await waitFor(() =>
    expect(api.updateProfile).toHaveBeenCalledWith({ username: "lan_anh" }),
  );
  expect(await screen.findByText("Đã lưu tên đăng nhập.")).toBeDefined();
});
