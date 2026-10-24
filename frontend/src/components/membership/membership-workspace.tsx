"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpenText,
  Check,
  MessageCircle,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { formatVnd, walletKey } from "@/components/wallet/wallet-workspace";
import {
  ApiError,
  membershipApi,
  profileApi,
  walletApi,
} from "@/lib/api/client";
import type {
  DiamondApplicationStatus,
  MembershipPlan,
  MembershipQuote,
  MembershipTier,
} from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";
import { CommunityChat, type CommunityChatRoom } from "./community-chat";
import { MembershipBenefitCenter } from "./membership-benefit-center";
import { MemberCard, membershipTiers } from "./member-card";

export function MembershipWorkspace({
  initialChatRoom = "MEMBER",
}: {
  initialChatRoom?: CommunityChatRoom;
}) {
  const user = useAuthUser();
  const client = useQueryClient();
  const queryKey = ["membership", user?.id];
  const membership = useQuery({
    queryKey,
    queryFn: membershipApi.overview,
    staleTime: 0,
    refetchInterval: 30_000,
  });
  const membershipLoaded = membership.data !== undefined;
  useEffect(() => {
    if (initialChatRoom === "MEMBER" || !membershipLoaded) return;
    const frame = requestAnimationFrame(() => {
      document
        .getElementById("community-chat")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    return () => cancelAnimationFrame(frame);
  }, [initialChatRoom, membershipLoaded]);
  const catalog = useQuery({
    queryKey: ["membership-plan-catalog"],
    queryFn: membershipApi.plans,
    staleTime: 60_000,
  });
  const profile = useQuery({
    queryKey: ["profile", user?.id],
    queryFn: profileApi.get,
  });
  const [selection, setSelection] = useState<{
    plan: MembershipPlan;
    key: string;
    renewalOptIn: boolean;
  } | null>(null);
  const [applicationStatement, setApplicationStatement] = useState("");
  const attemptKeys = useRef(new Map<string, string>());
  const quote = useQuery({
    queryKey: [
      "membership-quote",
      user?.id,
      selection?.plan.id,
      selection?.renewalOptIn,
    ],
    queryFn: () =>
      membershipApi.quote(selection!.plan.id, selection!.renewalOptIn),
    enabled: selection !== null,
    retry: false,
  });
  const diamondApplications = useQuery({
    queryKey: ["membership-diamond-applications", user?.id],
    queryFn: membershipApi.myDiamondApplications,
  });
  const submitDiamondApplication = useMutation({
    mutationFn: () =>
      membershipApi.submitDiamondApplication(applicationStatement.trim()),
    onSuccess: async () => {
      setApplicationStatement("");
      await client.invalidateQueries({
        queryKey: ["membership-diamond-applications", user?.id],
      });
      await client.invalidateQueries({ queryKey: ["membership-quote"] });
    },
  });
  const wallet = useQuery({
    queryKey: walletKey(user?.id),
    queryFn: walletApi.summary,
    enabled: selection !== null,
    staleTime: 0,
  });
  const buy = useMutation({
    mutationFn: (attempt: {
      plan: MembershipPlan;
      key: string;
      renewalOptIn: boolean;
      quote: MembershipQuote;
    }) =>
      membershipApi.purchase(attempt.plan.id, attempt.key, {
        expectedAmountMinor: attempt.quote.amountDueMinor,
        renewalOptIn: attempt.renewalOptIn,
      }),
    onSuccess: async (_result, attempt) => {
      attemptKeys.current.delete(attempt.plan.id);
      await client.invalidateQueries({ queryKey });
      await client.invalidateQueries({ queryKey: walletKey(user?.id) });
      await client.invalidateQueries({ queryKey: ["membership-chat"] });
      setSelection(null);
    },
  });
  if (membership.isPending)
    return <p role="status">Đang chuẩn bị thẻ thành viên…</p>;
  if (!membership.data)
    return (
      <div role="alert">
        <p>Chưa thể tải thẻ thành viên.</p>
        <Button onClick={() => void membership.refetch()}>Thử lại</Button>
      </div>
    );
  const current = membership.data;
  const hasMembershipLibrary = current.tier !== "MEMBER";
  const name = profile.data?.displayName?.trim() || "Thành viên Tinh Hoa Việt";
  return (
    <div className="mx-auto max-w-5xl space-y-8 pb-8 sm:space-y-10">
      <header>
        <p className="text-sm font-semibold tracking-wide text-[var(--theme-muted)]">
          MỘT CỘNG ĐỒNG · NHỮNG GIÁ TRỊ CHUNG
        </p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
          Thẻ thành viên
        </h1>
        <p className="mt-3 max-w-xl leading-7 text-[var(--theme-muted)]">
          Không gian kết nối dành cho những người trân trọng và lan tỏa tinh hoa
          Việt.
        </p>
      </header>
      <div className="grid items-center gap-6 lg:grid-cols-[1.4fr_1fr]">
        <MemberCard
          membership={current}
          name={name}
          avatarUrl={profile.data?.avatarUrl}
        />
        <div className="space-y-4">
          <h2 className="text-xl font-bold">Chào {name}</h2>
          <p className="leading-7 text-[var(--theme-muted)]">
            Hạng hội viên hiện tại: {membershipTiers[current.tier].name}. Xem
            thời hạn, quyền lợi và các lựa chọn quản lý bên dưới.
          </p>
          <a
            className="inline-flex min-h-11 items-center gap-2 font-semibold text-primary-700"
            href="#community-chat"
          >
            <MessageCircle aria-hidden="true" className="size-5" /> Vào phòng
            trò chuyện <ArrowRight aria-hidden="true" className="size-4" />
          </a>
          <div>
            <Link
              href="/wallet?returnTo=%2Fmembership"
              className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold underline"
            >
              <Wallet aria-hidden="true" className="size-4" /> Mở ví của tôi
            </Link>
          </div>
        </div>
      </div>
      {hasMembershipLibrary ? (
        <section className="flex flex-col gap-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold">
              <BookOpenText
                aria-hidden="true"
                className="size-5 text-emerald-700"
              />
              Thư viện nội dung hội viên
            </h2>
            <p className="mt-1 text-sm leading-6 text-[var(--theme-muted)]">
              Mở các bài viết và tài liệu được cấp quyền theo hạng hội viên của
              bạn.
            </p>
          </div>
          <Link
            className="inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-[var(--theme-border)] px-4 text-sm font-semibold sm:w-auto"
            href="/help"
          >
            Mở thư viện
          </Link>
        </section>
      ) : null}
      <CommunityChat
        key={initialChatRoom}
        tier={current.tier}
        initialRoom={initialChatRoom}
      />
      <MembershipBenefitCenter tier={current.tier} />
      <section aria-labelledby="tiers-heading">
        <h2 id="tiers-heading" className="text-2xl font-bold">
          Chọn cách bạn đồng hành
        </h2>
        <p className="mt-3 text-[var(--theme-muted)]">
          Mỗi hạng thẻ có không gian trò chuyện riêng. Bạn tự chọn mua hoặc gia
          hạn, không tự động trừ tiền.
        </p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {(Object.keys(membershipTiers) as MembershipTier[]).map((tier) => {
            const definition = membershipTiers[tier];
            const Icon = definition.icon;
            const plans = current.plans.filter((plan) => plan.tier === tier);
            const description =
              tier === "MEMBER"
                ? catalog.data?.member.description
                : plans[0]?.description;
            const benefits =
              tier === "MEMBER"
                ? (catalog.data?.member.benefits ?? [])
                : (plans[0]?.benefits ?? []);
            return (
              <article
                key={tier}
                className="flex flex-col rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-6"
              >
                <div className="flex items-center justify-between gap-2">
                  <Icon
                    aria-hidden="true"
                    className="size-7 text-primary-700"
                  />
                  {current.tier === tier && (
                    <span className="rounded-full bg-[var(--theme-elevated)] px-3 py-1 text-xs font-semibold">
                      Thẻ hiện tại
                    </span>
                  )}
                </div>
                <h3 className="mt-5 text-xl font-bold">{definition.name}</h3>
                <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
                  {description}
                </p>
                <ul className="my-6 flex-1 space-y-3">
                  {benefits.map((benefit) => (
                    <li
                      key={benefit}
                      className="flex items-start gap-2 text-sm leading-6"
                    >
                      <Check
                        aria-hidden="true"
                        className="mt-1 size-4 shrink-0 text-primary-700"
                      />
                      {benefit}
                    </li>
                  ))}
                </ul>
                {tier === "MEMBER" ? (
                  <p className="font-semibold">Miễn phí khi có tài khoản</p>
                ) : plans.length === 0 ? (
                  <p className="text-sm text-[var(--theme-muted)]">
                    Chưa mở đăng ký hạng thẻ này.
                  </p>
                ) : (
                  plans.map((plan) => (
                    <div
                      key={plan.id}
                      className="mt-3 border-t border-[var(--theme-border)] pt-4"
                    >
                      <p className="font-bold">
                        {formatVnd(plan.amountMinor)}{" "}
                        <span className="text-sm font-normal text-[var(--theme-muted)]">
                          / {plan.durationDays} ngày
                        </span>
                      </p>
                      <Button
                        className="mt-3 w-full"
                        disabled={buy.isPending}
                        variant="outline"
                        onClick={() => {
                          buy.reset();
                          const key =
                            attemptKeys.current.get(plan.id) ??
                            crypto.randomUUID();
                          attemptKeys.current.set(plan.id, key);
                          const renewalOptIn =
                            current.status === "ACTIVE" &&
                            current.tier === tier;
                          setSelection({ plan, key, renewalOptIn });
                        }}
                      >
                        {current.tier === tier
                          ? "Gia hạn bằng ví"
                          : "Đăng ký bằng ví"}
                      </Button>
                    </div>
                  ))
                )}
              </article>
            );
          })}
        </div>
      </section>
      <DiamondApplicationPanel
        applications={diamondApplications.data?.applications ?? []}
        isLoading={diamondApplications.isPending}
        isSubmitting={submitDiamondApplication.isPending}
        error={submitDiamondApplication.error}
        statement={applicationStatement}
        onStatementChange={setApplicationStatement}
        onSubmit={() => submitDiamondApplication.mutate()}
      />
      {current.purchases.length > 0 && (
        <section aria-label="Lịch sử thành viên">
          <h2 className="text-xl font-bold">Các lần đăng ký của bạn</h2>
          <ul className="mt-4 divide-y divide-[var(--theme-border)]">
            {current.purchases.map((item) => (
              <li
                key={item.id}
                className="flex flex-wrap justify-between gap-2 py-4 text-sm"
              >
                <span>
                  {membershipTiers[item.tier as MembershipTier]?.name ??
                    "Thành viên"}{" "}
                  · {new Date(item.createdAt).toLocaleDateString("vi-VN")}
                </span>
                <strong>{formatVnd(item.amountMinor)}</strong>
              </li>
            ))}
          </ul>
        </section>
      )}
      <ConfirmationDialog
        open={selection !== null}
        title="Xác nhận đăng ký thẻ"
        description={
          selection
            ? `${selection.plan.name}: xem báo giá nâng hạng và số tiền cuối cùng trước khi xác nhận thanh toán.`
            : ""
        }
        confirmLabel="Thanh toán bằng ví"
        onCancel={() => setSelection(null)}
        onConfirm={() => {
          if (selection && quote.data)
            buy.mutate({ ...selection, quote: quote.data });
        }}
        confirmDisabled={
          !wallet.data ||
          !quote.data ||
          quote.data.approvalRequired ||
          wallet.data.balanceMinor < (quote.data?.amountDueMinor ?? 0)
        }
        isPending={buy.isPending}
      >
        {quote.isPending ? (
          <p role="status" className="mb-3">
            Đang tính báo giá…
          </p>
        ) : quote.isError ? (
          <p role="alert" className="mb-3 text-red-700">
            {quote.error instanceof ApiError
              ? quote.error.message
              : "Chưa thể tính báo giá. Vui lòng thử lại."}
          </p>
        ) : quote.data ? (
          <div className="mb-4 space-y-2 rounded-lg bg-[var(--theme-elevated)] p-4 text-sm">
            <p>
              Giá gói: <strong>{formatVnd(quote.data.listPriceMinor)}</strong>
            </p>
            {quote.data.creditMinor > 0 ? (
              <p>
                Tín dụng ngày còn lại:{" "}
                <strong>−{formatVnd(quote.data.creditMinor)}</strong>
              </p>
            ) : null}
            <p>
              Cần thanh toán:{" "}
              <strong>{formatVnd(quote.data.amountDueMinor)}</strong>
            </p>
            <p>
              Thời hạn mới: {quote.data.durationDays} ngày, đến{" "}
              {new Date(quote.data.expiresAt).toLocaleDateString("vi-VN")}.
            </p>
            {quote.data.approvalRequired ? (
              <p className="font-semibold text-amber-900">
                Kim cương cần được xét duyệt trước khi thanh toán. Gửi yêu cầu
                tại phần{" "}
                <a className="underline" href="#diamond-application">
                  xét duyệt Kim cương
                </a>
                .
              </p>
            ) : null}
          </div>
        ) : null}
        {wallet.data ? (
          <p className="mb-3">
            Số dư ví: <strong>{formatVnd(wallet.data.balanceMinor)}</strong>
            {selection &&
              quote.data &&
              wallet.data.balanceMinor < quote.data.amountDueMinor && (
                <>
                  {" "}
                  · Còn thiếu{" "}
                  <strong>
                    {formatVnd(
                      quote.data.amountDueMinor - wallet.data.balanceMinor,
                    )}
                  </strong>
                  .{" "}
                  <Link
                    href="/wallet?returnTo=%2Fmembership"
                    className="inline-flex min-h-11 items-center underline"
                  >
                    Nạp tiền vào ví
                  </Link>
                </>
              )}
          </p>
        ) : (
          <p role="status" className="mb-3">
            {wallet.isError
              ? "Chưa thể kiểm tra ví. Vui lòng thử lại."
              : "Đang kiểm tra số dư ví…"}
          </p>
        )}
        <p>
          Không tự động gia hạn. Khi nâng hạng, số ngày còn lại được quy đổi
          thành tín dụng theo chính sách hiển thị trong báo giá.
        </p>
        {buy.isError && (
          <div role="alert" className="mt-3 text-red-700">
            <p>
              {buy.error instanceof ApiError
                ? buy.error.message
                : "Chưa thể đăng ký thẻ. Vui lòng kiểm tra lại giao dịch."}
            </p>
            <Link
              className="inline-flex min-h-11 items-center underline"
              href="/wallet?returnTo=%2Fmembership"
            >
              Nạp tiền vào ví
            </Link>
          </div>
        )}
      </ConfirmationDialog>
    </div>
  );
}

function DiamondApplicationPanel({
  applications,
  isLoading,
  isSubmitting,
  error,
  statement,
  onStatementChange,
  onSubmit,
}: {
  applications: {
    id: string;
    statement: string;
    status: DiamondApplicationStatus;
    decisionNote: string | null;
    createdAt: string;
  }[];
  isLoading: boolean;
  isSubmitting: boolean;
  error: unknown;
  statement: string;
  onStatementChange: (value: string) => void;
  onSubmit: () => void;
}) {
  const application = applications[0];
  const approved = applications.some((item) => item.status === "APPROVED");
  const needsResponse = application?.status === "INFO_REQUESTED";

  return (
    <section
      id="diamond-application"
      aria-labelledby="diamond-application-heading"
      className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-7"
    >
      <h2 id="diamond-application-heading" className="text-xl font-bold">
        Xét duyệt hội viên Kim cương
      </h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--theme-muted)]">
        Kim cương là cấp hội viên cộng đồng, không phải chứng nhận Tinh Hoa
        Việt. Gửi thông tin để Ban quản trị xem xét trước khi thanh toán.
      </p>
      {isLoading ? (
        <p role="status" className="mt-4">
          Đang tải trạng thái xét duyệt…
        </p>
      ) : null}
      {application ? (
        <div className="mt-4 rounded-lg bg-[var(--theme-elevated)] p-4 text-sm">
          <p className="font-semibold">
            Trạng thái: {applicationStatus(application.status)}
          </p>
          {application.decisionNote ? (
            <p className="mt-2">Ghi chú: {application.decisionNote}</p>
          ) : null}
          <p className="mt-2 text-xs text-[var(--theme-muted)]">
            Gửi ngày{" "}
            {new Date(application.createdAt).toLocaleDateString("vi-VN")}
          </p>
        </div>
      ) : null}
      {!approved &&
      (!application || needsResponse || application.status === "REJECTED") ? (
        <form
          className="mt-4 space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit();
          }}
        >
          <label
            className="block text-sm font-semibold"
            htmlFor="diamond-application-statement"
          >
            {needsResponse
              ? "Thông tin bổ sung"
              : "Giới thiệu lý do đăng ký Kim cương"}
          </label>
          <textarea
            id="diamond-application-statement"
            className="min-h-28 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 text-base"
            minLength={1}
            maxLength={5000}
            required
            value={statement}
            onChange={(event) => onStatementChange(event.target.value)}
          />
          <Button disabled={!statement.trim() || isSubmitting} type="submit">
            {isSubmitting
              ? "Đang gửi…"
              : needsResponse
                ? "Gửi thông tin bổ sung"
                : "Gửi yêu cầu xét duyệt"}
          </Button>
          {error ? (
            <p role="alert" className="text-sm text-red-700">
              Chưa gửi được yêu cầu. Vui lòng thử lại.
            </p>
          ) : null}
        </form>
      ) : null}
    </section>
  );
}

function applicationStatus(status: DiamondApplicationStatus): string {
  return {
    PENDING: "Đang chờ xét duyệt",
    INFO_REQUESTED: "Cần bổ sung thông tin",
    APPROVED: "Đã được duyệt",
    REJECTED: "Chưa được duyệt",
  }[status];
}
