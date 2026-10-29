"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { communityMemberApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import { Button } from "@/components/ui/button";

export function UsernameSettings() {
  const user = useAuthUser();
  const profile = useQuery({
    queryKey: ["community", "current-profile", user?.id],
    queryFn: () => communityMemberApi.currentProfile(),
    enabled: Boolean(user),
    staleTime: 60_000,
  });
  if (!user) return null;
  return (
    <section
      className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5"
      aria-labelledby="username-title"
    >
      <h2 id="username-title" className="font-bold">
        Tên đăng nhập
      </h2>
      <p className="mt-2 text-sm text-[var(--theme-muted)]">
        Dùng username này cùng mật khẩu để đăng nhập. Username cũng là địa chỉ
        hồ sơ cộng đồng, khác với tên hiển thị.
      </p>
      {profile.isPending ? (
        <p role="status" className="mt-3 text-sm">
          Đang tải tên đăng nhập…
        </p>
      ) : profile.data ? (
        <UsernameEditor initial={profile.data.username} />
      ) : (
        <button
          type="button"
          className="mt-2 min-h-11 underline"
          onClick={() => void profile.refetch()}
        >
          Tải lại tên đăng nhập
        </button>
      )}
    </section>
  );
}

function UsernameEditor({ initial }: { initial: string }) {
  const client = useQueryClient();
  const [value, setValue] = useState(
    initial.startsWith("member-") && initial.length === 39 ? "" : initial,
  );
  const save = useMutation({
    mutationFn: () =>
      communityMemberApi.updateProfile({
        username: value.trim().toLowerCase(),
      }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["community"] });
    },
  });
  return (
    <form
      className="mt-4 space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        save.mutate();
      }}
    >
      <label className="block text-sm font-semibold" htmlFor="account-username">
        Username
      </label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          className="ui-input-control min-w-0 flex-1"
          id="account-username"
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            save.reset();
          }}
          required
          minLength={3}
          maxLength={30}
          pattern="[A-Za-z0-9_\-]{3,30}"
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
          placeholder="Ví dụ: lan_anh"
        />
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? "Đang lưu…" : "Lưu tên đăng nhập"}
        </Button>
      </div>
      <p className="text-xs text-[var(--theme-muted)]">
        3–30 ký tự: chữ không dấu, số, dấu gạch ngang hoặc gạch dưới. Tài khoản
        chỉ dùng Google cần đặt mật khẩu qua “Quên mật khẩu” trước khi đăng nhập
        bằng username.
      </p>
      {save.isSuccess && (
        <p role="status" className="text-sm">
          Đã lưu tên đăng nhập.
        </p>
      )}
      {save.isError && (
        <p role="alert" className="text-sm text-[var(--theme-text)]">
          Chưa lưu được username. Tên có thể đã được sử dụng hoặc không hợp lệ;
          hãy chọn tên khác rồi thử lại.
        </p>
      )}
    </form>
  );
}
