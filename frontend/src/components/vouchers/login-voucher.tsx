"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Gift, X } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useId, useRef, useState, type CSSProperties } from "react";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { voucherApi } from "@/lib/api/client";
import { isCustomerAccount } from "@/lib/auth/role-workspaces";

export function LoginVoucher({
  userId,
  roles,
  isEmployee = false,
  permissions = [],
}: {
  userId: string | null;
  roles: readonly string[];
  isEmployee?: boolean;
  permissions?: readonly string[];
}) {
  const eligible = isCustomerAccount({ roles, isEmployee, permissions });
  return userId && eligible ? (
    <AccountVoucher key={userId} userId={userId} />
  ) : null;
}

function AccountVoucher({ userId }: { userId: string }) {
  const client = useQueryClient();
  const pathname = usePathname() ?? "";
  const criticalPath =
    /^(\/payments|\/checkout|\/dossiers\/new|\/dossiers\/[^/]+\/edit)(\/|$)/.test(
      pathname,
    );
  const [mayOpen, setMayOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();
  const trigger = ["/", "/dashboard", "/workspace"].includes(pathname)
    ? "DASHBOARD"
    : "LOGIN";
  const offerKey = ["vouchers", "offer", userId, trigger];
  const offer = useQuery({
    queryKey: offerKey,
    enabled: !criticalPath,
    queryFn: async () => {
      const available = await voucherApi.offer(trigger);
      try {
        if (
          available &&
          sessionStorage.getItem(`voucher-dismissed:${userId}:${available.id}`)
        )
          return null;
      } catch {
        /* Storage may be blocked; server still prevents duplicate claims. */
      }
      return available;
    },
    staleTime: 60_000,
    refetchInterval: (query) => (query.state.data ? false : 30_000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: (query) => (query.state.data ? false : "always"),
    retry: false,
  });
  const claim = useMutation({
    mutationFn: (campaignId: string) => voucherApi.claim(campaignId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["vouchers", "mine", userId] });
      void client.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
  const available = offer.data;
  const display = available?.policy?.presentation;
  const issuedId = available?.claimedVoucherId;
  useEffect(() => {
    if (!issuedId) return;
    void client.invalidateQueries({ queryKey: ["vouchers", "mine", userId] });
    void client.invalidateQueries({ queryKey: ["notifications"] });
  }, [client, issuedId, userId]);
  const destination = available?.policy?.serviceCodes.includes("MEMBERSHIP")
    ? "/membership"
    : available?.policy?.serviceCodes.includes("ADVERTISING")
      ? "/advertising"
      : "/dossiers";
  const ctaColor = display?.ctaColor ?? "#9d0000";
  const rgb = [1, 3, 5].map((index) =>
    parseInt(ctaColor.slice(index, index + 2), 16),
  );
  const brightness = (rgb[0]! * 299 + rgb[1]! * 587 + rgb[2]! * 114) / 1000;
  const ctaText = brightness > 145 ? "#241515" : "#ffffff";
  const hoverColor = `#${rgb
    .map((value) =>
      Math.floor(value * 0.78)
        .toString(16)
        .padStart(2, "0"),
    )
    .join("")}`;

  useEffect(() => {
    if (!available || criticalPath) return;
    const check = () => {
      const anotherModal = [
        ...document.querySelectorAll(
          'dialog[open], [role="dialog"][aria-modal="true"]',
        ),
      ].some((element) => element !== dialog.current);
      const focused = document.activeElement;
      const editing =
        focused instanceof HTMLElement &&
        Boolean(focused.closest("form")) &&
        /INPUT|TEXTAREA|SELECT/.test(focused.tagName);
      setMayOpen(!criticalPath && !anotherModal && !editing);
    };
    check();
    const observer = new MutationObserver(check);
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["open", "aria-modal"],
    });
    const onFocus = () => queueMicrotask(check);
    document.addEventListener("focusin", onFocus);
    document.addEventListener("focusout", onFocus);
    return () => {
      observer.disconnect();
      document.removeEventListener("focusin", onFocus);
      document.removeEventListener("focusout", onFocus);
    };
  }, [available, criticalPath]);

  function dismiss() {
    if (available) {
      void voucherApi
        .presentation?.(available.id, "DISMISSED")
        .catch(() => undefined);
      try {
        sessionStorage.setItem(
          `voucher-dismissed:${userId}:${available.id}`,
          "1",
        );
      } catch {
        /* Dismissal still works without browser storage. */
      }
    }
    client.setQueryData(offerKey, null);
  }

  useEffect(() => {
    const element = dialog.current;
    if (!available || !element || !mayOpen) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    element.showModal();
    void voucherApi.presentation?.(available.id, "SEEN").catch(() => undefined);
    element.querySelector<HTMLButtonElement>("[data-voucher-claim]")?.focus();
    return () => {
      element.close();
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus();
    };
  }, [available, mayOpen]);

  if (!available || !mayOpen) return null;

  return (
    <dialog
      ref={dialog}
      style={
        {
          backgroundColor: display?.backgroundColor,
          color: display?.textColor,
          borderRadius: display?.borderRadius,
          "--theme-accent": ctaColor,
          "--theme-accent-contrast": ctaText,
          "--theme-text": display?.textColor,
          "--theme-muted": display?.textColor,
          "--theme-elevated": display?.backgroundColor,
          "--voucher-hover-color": hoverColor,
          "--voucher-overlay": display?.overlay ?? 0.7,
        } as CSSProperties
      }
      data-template={display?.template}
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      className="voucher-dialog fixed inset-0 m-auto max-h-[92dvh] w-[calc(100%-2rem)] max-w-3xl overflow-y-auto rounded-2xl border border-amber-200 bg-[#fff9ed] p-0 text-[#671b16] shadow-2xl backdrop:bg-black/70"
      onCancel={(event) => {
        event.preventDefault();
        dismiss();
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          dismiss();
        }
      }}
    >
      <div
        className={`relative grid ${display?.template === "MINIMAL" ? "" : "sm:grid-cols-2"}`}
      >
        <button
          aria-label="Đóng thông báo voucher"
          className="absolute right-2 top-2 z-10 grid size-11 place-items-center rounded-full bg-[#fff9ed] text-[#671b16] focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50"
          onClick={dismiss}
        >
          <X aria-hidden="true" className="size-5" />
        </button>
        {display?.template !== "MINIMAL" && (
          <div className="voucher-dialog__image flex items-center justify-center bg-[#f4dfb5]">
            <picture className="w-full">
              {display?.mobileImageAssetId && (
                <source
                  media="(max-width: 639px)"
                  srcSet={`/api/v1/promotion-media/${display.mobileImageAssetId}`}
                />
              )}
              <Image
                src={
                  display?.imageAssetId
                    ? `/api/v1/promotion-media/${display.imageAssetId}`
                    : available.imagePath
                }
                unoptimized={
                  Boolean(display?.imageAssetId) ||
                  available.imagePath.startsWith("/api/")
                }
                style={{
                  objectFit: display?.imageFit,
                  objectPosition: `${display?.focalX ?? 50}% ${display?.focalY ?? 50}%`,
                }}
                alt={
                  display?.altText ||
                  "Voucher vàng Tinh Hoa Việt — Tri ân thành viên"
                }
                width={1122}
                height={1402}
                sizes="(max-width: 640px) 100vw, 384px"
                className="max-h-[34dvh] w-full object-contain sm:max-h-[80dvh]"
              />
            </picture>
          </div>
        )}
        <div className="voucher-dialog__body flex flex-col justify-center gap-4 p-5 sm:p-8 sm:pt-14">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest opacity-80">
            <Gift aria-hidden="true" className="size-4" />{" "}
            {display?.subtitle || "Món quà tri ân"}
          </p>
          <h2
            id={titleId}
            className="text-2xl font-bold leading-tight sm:text-3xl"
          >
            {claim.isSuccess ? "Đã nhận voucher!" : available.title}
          </h2>
          <p id={descriptionId} className="text-sm leading-6">
            {claim.isSuccess
              ? "Voucher đã được lưu vào tài khoản của bạn. Bạn có thể xem lại bất cứ lúc nào."
              : available.description}
          </p>
          <p className="text-sm leading-6 opacity-85">{available.terms}</p>
          <p className="text-xs opacity-85">
            {issuedId && available.expiresAt
              ? `Sử dụng đến ${new Date(available.expiresAt).toLocaleDateString("vi-VN")}.`
              : `Hiệu lực ${available.validityDays} ngày kể từ khi nhận.`}
          </p>
          {claim.isError && (
            <p role="alert" className="text-sm font-medium text-red-800">
              Chưa nhận được voucher. Vui lòng thử lại.
            </p>
          )}
          {claim.isSuccess || issuedId ? (
            <>
              <p
                role="status"
                className="flex items-center gap-2 text-sm font-semibold"
              >
                <CheckCircle2 aria-hidden="true" className="size-5" /> Nhận quà
                thành công
              </p>
              <Link
                href={issuedId ? destination : "/vouchers"}
                onClick={() => {
                  void voucherApi
                    .presentation?.(available.id, "CLICKED")
                    .catch(() => undefined);
                  dismiss();
                }}
                style={{ backgroundColor: ctaColor, color: ctaText }}
                className="inline-flex min-h-11 items-center justify-center rounded-lg bg-[#720000] px-4 py-3 text-sm font-semibold text-white focus-visible:outline-2 focus-visible:outline-offset-2"
              >
                {issuedId
                  ? display?.primaryCta || "Sử dụng ưu đãi"
                  : "Xem voucher của tôi"}
              </Link>
              <Button variant="ghost" onClick={dismiss}>
                Tiếp tục khám phá
              </Button>
            </>
          ) : (
            <>
              <Button
                data-voucher-claim
                style={{ backgroundColor: ctaColor, color: ctaText }}
                disabled={claim.isPending}
                onClick={() => {
                  void voucherApi
                    .presentation?.(available.id, "CLICKED")
                    .catch(() => undefined);
                  claim.mutate(available.id);
                }}
              >
                {claim.isPending
                  ? "Đang nhận voucher…"
                  : display?.primaryCta || "Nhận voucher ngay"}
              </Button>
              <Button variant="ghost" onClick={dismiss}>
                {display?.secondaryCta || "Để sau"}
              </Button>
            </>
          )}
        </div>
      </div>
    </dialog>
  );
}
