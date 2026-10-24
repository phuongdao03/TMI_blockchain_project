"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, membershipApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import { formatVnd } from "@/components/wallet/wallet-workspace";
import type { MembershipBenefitRequest } from "@/lib/api/types";
import { membershipTiers } from "./member-card";
import { benefitLabel } from "./membership-benefit-center";
import { MembershipChatAccessAdmin } from "./membership-chat-access-admin";

export function MembershipAdminWorkspace() {
  const user = useAuthUser();
  const allowed = Boolean(
    user?.roles.includes("SUPER_ADMIN") ||
      user?.permissions?.includes("memberships.manage"),
  );
  const client = useQueryClient();
  const plans = useQuery({
    queryKey: ["membership", user?.id],
    queryFn: membershipApi.overview,
    enabled: allowed,
  });
  const [name, setName] = useState("");
  const [tier, setTier] = useState<"SILVER" | "COMPANION" | "PRESTIGE">("SILVER");
  const [amount, setAmount] = useState("");
  const [days, setDays] = useState("");
  const [description, setDescription] = useState("");
  const [benefitsText, setBenefitsText] = useState("");
  const [conditions, setConditions] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [benefitReviewNote, setBenefitReviewNote] = useState("");
  const diamondApplications = useQuery({
    queryKey: ["membership-diamond-applications-admin", user?.id],
    queryFn: () => membershipApi.diamondApplications(),
    enabled: allowed,
  });
  const benefitRequests = useQuery({
    queryKey: ["membership-benefit-requests-admin", user?.id],
    queryFn: () => membershipApi.benefitRequests(),
    enabled: allowed,
  });
  const publish = useMutation({
    mutationFn: () =>
      membershipApi.publishPlan({
        name,
        tier,
        amountMinor: Number(amount),
        durationDays: Number(days),
        description,
        benefits: benefitsText
          .split("\n")
          .map((benefit) => benefit.trim())
          .filter(Boolean),
        conditions,
      }),
    onSuccess: async () => {
      setName("");
      setAmount("");
      setDays("");
      setDescription("");
      setBenefitsText("");
      setConditions("");
      await client.invalidateQueries({ queryKey: ["membership"] });
    },
  });
  const retire = useMutation({
    mutationFn: membershipApi.retirePlan,
    onSuccess: () => client.invalidateQueries({ queryKey: ["membership"] }),
  });
  const reviewApplication = useMutation({
    mutationFn: (input: {
      id: string;
      action: "approve" | "reject" | "request-info";
    }) => membershipApi.reviewDiamondApplication(input.id, input.action, reviewNote),
    onSuccess: async () => {
      setReviewNote("");
      await client.invalidateQueries({
        queryKey: ["membership-diamond-applications-admin", user?.id],
      });
      await client.invalidateQueries({ queryKey: ["membership-diamond-applications"] });
    },
  });
  const reviewBenefit = useMutation({
    mutationFn: (input: {
      id: string;
      action: "approve" | "reject" | "request-info" | "complete";
    }) =>
      membershipApi.reviewBenefitRequest(
        input.id,
        input.action,
        benefitReviewNote,
      ),
    onSuccess: async () => {
      setBenefitReviewNote("");
      await client.invalidateQueries({
        queryKey: ["membership-benefit-requests-admin", user?.id],
      });
      await client.invalidateQueries({ queryKey: ["membership-benefit-requests"] });
      await client.invalidateQueries({ queryKey: ["membership-collaboration-needs"] });
    },
  });
  if (!allowed)
    return <p role="alert">Bạn không có quyền quản lý gói thành viên.</p>;
  const inputClass =
    "mt-2 min-h-12 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-base";
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <h1 className="text-3xl font-bold">Gói thẻ thành viên</h1>
        <p className="mt-3 leading-7 text-[var(--theme-muted)]">
          Cấu hình giá và thời hạn cho từng hạng thẻ. Gói mới không thay đổi
          khoản thu hoặc thời hạn đã bán.
        </p>
      </header>
      <MembershipChatAccessAdmin />
      <form
        className="grid gap-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault();
          publish.mutate();
        }}
      >
        <label className="text-sm font-semibold">
          Tên gói
          <input
            className={inputClass}
            required
            maxLength={120}
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={publish.isPending}
          />
        </label>
        <label className="text-sm font-semibold">
          Hạng thẻ
          <select
            className={inputClass}
            value={tier}
            onChange={(event) =>
              setTier(event.target.value as "SILVER" | "COMPANION" | "PRESTIGE")
            }
            disabled={publish.isPending}
          >
            <option value="SILVER">Kết nối Bạc</option>
            <option value="COMPANION">Đồng hành</option>
            <option value="PRESTIGE">Tinh hoa Kim cương</option>
          </select>
        </label>
        <label className="text-sm font-semibold">
          Giá gói (VNĐ)
          <input
            className={inputClass}
            type="number"
            inputMode="numeric"
            min={1}
            max={1_000_000_000}
            step={1}
            required
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            disabled={publish.isPending}
          />
        </label>
        <label className="text-sm font-semibold">
          Thời hạn (ngày)
          <input
            className={inputClass}
            type="number"
            inputMode="numeric"
            min={1}
            max={3660}
            step={1}
            required
            value={days}
            onChange={(event) => setDays(event.target.value)}
            disabled={publish.isPending}
          />
        </label>
        <label className="text-sm font-semibold sm:col-span-2">
          Mô tả
          <textarea
            className={inputClass}
            required
            maxLength={500}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            disabled={publish.isPending}
            rows={2}
          />
        </label>
        <label className="text-sm font-semibold sm:col-span-2">
          Quyền lợi bổ sung (mỗi dòng một quyền lợi)
          <textarea
            className={inputClass}
            required
            maxLength={5000}
            value={benefitsText}
            onChange={(event) => setBenefitsText(event.target.value)}
            disabled={publish.isPending}
            rows={5}
          />
        </label>
        <label className="text-sm font-semibold sm:col-span-2">
          Điều kiện
          <textarea
            className={inputClass}
            maxLength={1000}
            value={conditions}
            onChange={(event) => setConditions(event.target.value)}
            disabled={publish.isPending}
            rows={2}
          />
        </label>
        <Button
          className="sm:col-span-2"
          type="submit"
          disabled={
            publish.isPending ||
            !name.trim() ||
            !description.trim() ||
            !benefitsText.trim()
          }
        >
          {publish.isPending ? "Đang mở đăng ký…" : "Mở đăng ký gói"}
        </Button>
        {publish.isError && (
          <p className="text-red-700 sm:col-span-2" role="alert">
            {publish.error instanceof ApiError
              ? publish.error.message
              : "Chưa thể mở gói. Vui lòng thử lại."}
          </p>
        )}
        {publish.isSuccess && (
          <p role="status" className="sm:col-span-2">
            Đã mở gói thành viên.
          </p>
        )}
      </form>
      <section>
        <h2 className="text-xl font-bold">Gói đang mở đăng ký</h2>
        {plans.isPending ? (
          <p role="status">Đang tải gói…</p>
        ) : plans.isError ? (
          <p role="alert">Chưa thể tải danh sách gói.</p>
        ) : plans.data?.plans.length === 0 ? (
          <p className="mt-3 text-[var(--theme-muted)]">
            Chưa có gói trả phí nào được mở.
          </p>
        ) : (
          <ul className="mt-4 divide-y divide-[var(--theme-border)]">
            {plans.data?.plans.map((plan) => (
              <li
                key={plan.id}
                className="flex flex-wrap items-center justify-between gap-3 py-4"
              >
                <div>
                  <h3 className="font-bold">{plan.name}</h3>
                  <p className="mt-1 text-sm">
                    {membershipTiers[plan.tier].name} ·{" "}
                    {formatVnd(plan.amountMinor)} / {plan.durationDays} ngày
                  </p>
                </div>
                <Button
                  variant="outline"
                  disabled={retire.isPending}
                  onClick={() => retire.mutate(plan.id)}
                >
                  Ngừng đăng ký mới
                </Button>
              </li>
            ))}
          </ul>
        )}
        {retire.isError && (
          <p role="alert" className="text-red-700">
            Chưa thể ngừng đăng ký gói.
          </p>
        )}
        <p className="mt-4 text-sm text-[var(--theme-muted)]">
          Ngừng đăng ký mới không thu hồi thẻ đã mua.
        </p>
      </section>
      <section aria-labelledby="diamond-applications-heading">
        <h2 id="diamond-applications-heading" className="text-xl font-bold">
          Yêu cầu xét duyệt Kim cương
        </h2>
        <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
          Duyệt hội viên cộng đồng độc lập với quy trình thẩm định hồ sơ đề cử.
        </p>
        <label className="mt-4 block text-sm font-semibold" htmlFor="diamond-review-note">
          Ghi chú quyết định
        </label>
        <textarea
          id="diamond-review-note"
          className={inputClass}
          maxLength={2000}
          minLength={1}
          value={reviewNote}
          onChange={(event) => setReviewNote(event.target.value)}
        />
        {diamondApplications.isPending ? (
          <p role="status" className="mt-3">Đang tải yêu cầu…</p>
        ) : diamondApplications.isError ? (
          <p role="alert" className="mt-3 text-red-700">Chưa thể tải yêu cầu xét duyệt.</p>
        ) : diamondApplications.data?.applications.length ? (
          <ul className="mt-4 divide-y divide-[var(--theme-border)]">
            {diamondApplications.data.applications.map((application) => (
              <li key={application.id} className="space-y-3 py-4">
                <div className="flex flex-wrap justify-between gap-2 text-sm">
                  <strong>{application.userId}</strong>
                  <span>{diamondApplicationStatus(application.status)}</span>
                </div>
                <p className="whitespace-pre-wrap text-sm leading-6">{application.statement}</p>
                {application.decisionNote ? (
                  <p className="text-sm text-[var(--theme-muted)]">Ghi chú trước đó: {application.decisionNote}</p>
                ) : null}
                {application.status === "PENDING" || application.status === "INFO_REQUESTED" ? (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      disabled={reviewApplication.isPending || !reviewNote.trim()}
                      onClick={() => reviewApplication.mutate({ id: application.id, action: "approve" })}
                    >Duyệt</Button>
                    <Button
                      variant="outline"
                      disabled={reviewApplication.isPending || !reviewNote.trim()}
                      onClick={() => reviewApplication.mutate({ id: application.id, action: "request-info" })}
                    >Yêu cầu bổ sung</Button>
                    <Button
                      variant="outline"
                      disabled={reviewApplication.isPending || !reviewNote.trim()}
                      onClick={() => reviewApplication.mutate({ id: application.id, action: "reject" })}
                    >Từ chối</Button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-[var(--theme-muted)]">Chưa có yêu cầu Kim cương.</p>
        )}
        {reviewApplication.isError ? (
          <p role="alert" className="mt-3 text-red-700">
            {reviewApplication.error instanceof ApiError
              ? reviewApplication.error.message
              : "Chưa thể cập nhật yêu cầu xét duyệt."}
          </p>
        ) : null}
      </section>
      <section aria-labelledby="benefit-requests-heading">
        <h2 className="text-xl font-bold" id="benefit-requests-heading">
          Yêu cầu quyền lợi cần điều phối
        </h2>
        <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
          Duyệt nhu cầu hợp tác để công bố cho hội viên đủ hạng; tiếp nhận các
          yêu cầu tư vấn, kết nối và câu chuyện để đội ngũ xử lý.
        </p>
        <label className="mt-4 block text-sm font-semibold" htmlFor="benefit-review-note">
          Ghi chú xử lý
        </label>
        <textarea
          id="benefit-review-note"
          className={inputClass}
          maxLength={2000}
          minLength={1}
          value={benefitReviewNote}
          onChange={(event) => setBenefitReviewNote(event.target.value)}
        />
        {benefitRequests.isPending ? (
          <p className="mt-3 text-sm text-[var(--theme-muted)]" role="status">
            Đang tải yêu cầu…
          </p>
        ) : benefitRequests.isError ? (
          <p className="mt-3 text-sm text-red-700" role="alert">
            Chưa thể tải hàng đợi quyền lợi.
          </p>
        ) : benefitRequests.data.requests.length ? (
          <ul className="mt-4 divide-y divide-[var(--theme-border)]">
            {benefitRequests.data.requests.map((item) => (
              <li className="space-y-3 py-4" key={item.id}>
                <div className="flex flex-wrap justify-between gap-2 text-sm">
                  <strong>{benefitLabel(item.benefit)}</strong>
                  <span>{membershipBenefitStatus(item.status)}</span>
                </div>
                <p className="text-xs text-[var(--theme-muted)]">
                  Hội viên {item.userId} · chu kỳ từ{" "}
                  {new Date(item.cycleStartedAt).toLocaleDateString("vi-VN")}
                </p>
                <p className="whitespace-pre-wrap text-sm leading-6">
                  {item.statement}
                </p>
                {item.decisionNote ? (
                  <p className="text-sm text-[var(--theme-muted)]">
                    Ghi chú trước đó: {item.decisionNote}
                  </p>
                ) : null}
                {item.status === "PENDING" || item.status === "INFO_REQUESTED" ? (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      disabled={reviewBenefit.isPending || !benefitReviewNote.trim()}
                      onClick={() => reviewBenefit.mutate({ id: item.id, action: "approve" })}
                    >
                      Tiếp nhận
                    </Button>
                    <Button
                      variant="outline"
                      disabled={reviewBenefit.isPending || !benefitReviewNote.trim()}
                      onClick={() => reviewBenefit.mutate({ id: item.id, action: "request-info" })}
                    >
                      Yêu cầu bổ sung
                    </Button>
                    <Button
                      variant="outline"
                      disabled={reviewBenefit.isPending || !benefitReviewNote.trim()}
                      onClick={() => reviewBenefit.mutate({ id: item.id, action: "reject" })}
                    >
                      Từ chối
                    </Button>
                  </div>
                ) : item.status === "APPROVED" ? (
                  <Button
                    disabled={reviewBenefit.isPending || !benefitReviewNote.trim()}
                    onClick={() => reviewBenefit.mutate({ id: item.id, action: "complete" })}
                  >
                    Đánh dấu hoàn tất
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-[var(--theme-muted)]">
            Chưa có yêu cầu quyền lợi.
          </p>
        )}
        {reviewBenefit.isError ? (
          <p className="mt-3 text-sm text-red-700" role="alert">
            {reviewBenefit.error instanceof ApiError
              ? reviewBenefit.error.message
              : "Chưa thể cập nhật yêu cầu quyền lợi."}
          </p>
        ) : null}
      </section>
    </div>
  );
}

function diamondApplicationStatus(status: string): string {
  return {
    PENDING: "Chờ xét duyệt",
    INFO_REQUESTED: "Chờ bổ sung thông tin",
    APPROVED: "Đã duyệt",
    REJECTED: "Từ chối",
  }[status] ?? status;
}

function membershipBenefitStatus(status: MembershipBenefitRequest["status"]): string {
  return {
    PENDING: "Chờ xử lý",
    INFO_REQUESTED: "Chờ hội viên bổ sung",
    APPROVED: "Đang thực hiện",
    COMPLETED: "Hoàn tất",
    REJECTED: "Từ chối",
  }[status];
}
