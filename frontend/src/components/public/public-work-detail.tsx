"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Blocks,
  CalendarDays,
  CircleHelp,
  ExternalLink,
  FileCheck2,
  FileText,
  RotateCcw,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AdaptiveVideo } from "@/components/public/adaptive-video";
import { WorkCoverPlaceholder } from "@/components/public/work-cover-placeholder";
import { PublicWorkCard } from "@/components/public/public-work-card";
import { PublicWorkShareControls } from "@/components/public/public-work-share-controls";
import { Button } from "@/components/ui/button";
import { ApiError, publicApi } from "@/lib/api/client";
import type {
  PublicWorkDetail,
  PublicWorkDetailMedia,
  Verification,
} from "@/lib/api/types";

export function PublicWorkDetailPage({
  initialDetail,
  slug,
}: {
  initialDetail?: PublicWorkDetail;
  slug: string;
}) {
  const detail = useQuery({
    queryKey: ["public-work-detail", slug],
    queryFn: () => publicApi.work(slug),
    initialData: initialDetail,
    retry: false,
    refetchOnWindowFocus: true,
  });
  const error = detail.error as ApiError | null;

  if (detail.isPending) return <DetailSkeleton />;
  if (error?.status === 404) return <UnavailableWork />;
  if (detail.error || !detail.data) {
    return (
      <div className="public-status-layout">
        <section
          aria-labelledby="work-load-error-title"
          className="public-status-panel"
          role="status"
        >
          <CircleHelp
            aria-hidden="true"
            className="public-status-panel__icon mx-auto size-9"
          />
          <h1
            className="public-status-panel__title mt-5 text-2xl font-bold"
            id="work-load-error-title"
          >
            Chưa thể tải tác phẩm
          </h1>
          <p className="public-status-panel__copy mt-2 text-sm leading-6">
            Dịch vụ công khai đang gián đoạn. Hãy thử lại sau ít phút.
          </p>
          <Button className="mt-5" onClick={() => detail.refetch()}>
            <RotateCcw className="size-4" /> Thử lại
          </Button>
        </section>
      </div>
    );
  }
  return <PublicWorkPresentation detail={detail.data} />;
}

export function PublicWorkPresentation({
  detail,
  preview = false,
}: {
  detail: PublicWorkDetail;
  preview?: boolean;
}) {
  useEffect(() => {
    if (!preview)
      void publicApi.recordView(detail.canonicalSlug).catch(() => undefined);
  }, [detail.canonicalSlug, preview]);

  const verification = useQuery({
    queryKey: [
      "public-work-verification",
      detail.certificate?.certificateNumber,
    ],
    queryFn: () =>
      publicApi.verifyNumber(detail.certificate!.certificateNumber),
    enabled: !preview && Boolean(detail.certificate?.certificateNumber),
    retry: false,
    staleTime: 60_000,
  });
  return (
    <article className="public-theme-surface @container/work relative isolate min-w-0 overflow-hidden">
      <header className="border-b border-white/10 px-4 py-7 @min-[40rem]/work:px-6 @min-[64rem]/work:py-14">
        <div className="mx-auto max-w-[90rem]">
          <nav
            aria-label="Breadcrumb"
            className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm leading-6 text-slate-500"
          >
            <Link
              className="inline-flex min-h-11 items-center gap-1 hover:text-white"
              href="/works"
            >
              <ArrowLeft className="size-4" /> Danh sách đề cử
            </Link>
            <span aria-hidden="true">/</span>
            <span>{detail.categoryName}</span>
          </nav>
          <div className="mt-5 grid grid-cols-1 gap-6 @min-[64rem]/work:mt-9 @min-[64rem]/work:grid-cols-[minmax(0,1fr)_22rem] @min-[64rem]/work:items-end">
            <div className="min-w-0">
              <p className="text-xs font-bold tracking-[0.2em] text-gold-300 uppercase">
                {detail.categoryName}
              </p>
              <h1 className="mt-3 max-w-5xl text-3xl leading-tight font-bold break-words tracking-[-0.035em] text-white @min-[40rem]/work:text-5xl @min-[64rem]/work:text-6xl">
                {detail.title}
              </h1>
              <p className="mt-4 max-w-3xl text-base leading-7 break-words text-slate-300 @min-[40rem]/work:text-lg">
                {detail.shortDescription}
              </p>
            </div>
            <dl className="grid min-w-0 gap-4 border-t border-white/10 pt-5 text-sm @min-[64rem]/work:border-t-0 @min-[64rem]/work:border-l @min-[64rem]/work:pt-0 @min-[64rem]/work:pl-5">
              <div>
                <dt className="text-xs tracking-wide text-slate-500 uppercase">
                  Tác giả công khai
                </dt>
                <dd className="mt-1 flex items-start gap-2 leading-6 font-bold text-white">
                  <UserRound className="mt-1 size-4 shrink-0 text-gold-300" />
                  <span className="min-w-0 break-words">
                    {detail.authorDisplayName || "Chưa công bố"}
                  </span>
                </dd>
              </div>
              {detail.organizationDisplayName ? (
                <div>
                  <dt className="text-xs tracking-wide text-slate-500 uppercase">
                    Tổ chức
                  </dt>
                  <dd className="mt-1 font-bold text-white">
                    {detail.organizationDisplayName}
                  </dd>
                </div>
              ) : null}
              <div>
                <dt className="text-xs tracking-wide text-slate-500 uppercase">
                  Ngày công bố
                </dt>
                <dd className="mt-1 flex items-start gap-2 leading-6 text-white">
                  <CalendarDays className="mt-1 size-4 shrink-0 text-gold-300" />
                  {preview ? (
                    <span>Chưa công bố · bản xem trước</span>
                  ) : (
                    <time dateTime={detail.publishedAt}>
                      {new Intl.DateTimeFormat("vi-VN", {
                        dateStyle: "long",
                      }).format(new Date(detail.publishedAt))}
                    </time>
                  )}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[90rem] px-4 py-6 @min-[40rem]/work:px-6 @min-[64rem]/work:px-8 @min-[64rem]/work:py-12">
        <PublicGallery media={detail.media} title={detail.title} />
        <div className="mt-8 grid grid-cols-1 gap-8 @min-[64rem]/work:mt-12 @min-[64rem]/work:grid-cols-[minmax(0,1fr)_24rem]">
          <div className="min-w-0">
            <section
              aria-labelledby="about-work-heading"
              className="border-t border-white/10 pt-7"
            >
              <p className="text-xs font-bold tracking-[0.2em] text-primary-400 uppercase">
                Câu chuyện đề cử
              </p>
              <h2
                className="mt-2 text-3xl font-bold text-white"
                id="about-work-heading"
              >
                Về tác phẩm
              </h2>
              {detail.fullDescription ? (
                <p className="mt-6 max-w-4xl whitespace-pre-wrap break-words text-base leading-8 text-slate-300">
                  {detail.fullDescription}
                </p>
              ) : (
                <p className="mt-5 text-sm text-slate-500">
                  Tác phẩm chưa có phần giới thiệu mở rộng.
                </p>
              )}
              <div className="mt-8 flex flex-wrap gap-2">
                {detail.tags.map((tag) => (
                  <Link
                    className="rounded-full border border-white/10 px-3 py-1.5 text-xs font-bold text-slate-300 hover:border-gold-300"
                    href={`/works?tag=${encodeURIComponent(tag.slug)}`}
                    key={tag.slug}
                  >
                    #{tag.name}
                  </Link>
                ))}
              </div>
            </section>
            {!preview ? <PublicWorkShareControls detail={detail} /> : null}
          </div>
          <aside className="h-fit min-w-0 divide-y divide-white/10 border-y border-white/10">
            <CertificatePanel certificate={detail.certificate} />
            <ProofPanel
              proof={detail.proof}
              verification={verification.data}
              verificationPending={
                verification.isPending &&
                verification.fetchStatus === "fetching"
              }
            />
          </aside>
        </div>

        {detail.relatedWorks.length ? (
          <section
            aria-labelledby="related-heading"
            className="mt-16 border-t border-white/10 pt-10"
          >
            <p className="text-xs font-bold tracking-[0.2em] text-gold-300 uppercase">
              Khám phá tiếp
            </p>
            <h2
              className="mt-2 text-3xl font-bold text-white"
              id="related-heading"
            >
              Tác phẩm liên quan
            </h2>
            <div className="mt-6 grid gap-4 @min-[40rem]/work:grid-cols-2 @min-[64rem]/work:grid-cols-3">
              {detail.relatedWorks.map((work, index) => (
                <PublicWorkCard
                  key={work.id}
                  position={index + 1}
                  source="list"
                  work={work}
                />
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </article>
  );
}

function PublicGallery({
  media,
  title,
}: {
  media: PublicWorkDetailMedia[];
  title: string;
}) {
  const [selectedId, setSelectedId] = useState(
    media.find((item) => item.isThumbnail)?.id ?? media[0]?.id,
  );
  const selected = media.find((item) => item.id === selectedId) ?? media[0];
  if (!selected)
    return (
      <WorkCoverPlaceholder title={title} label="Tác phẩm được ghi nhận" />
    );
  return (
    <section aria-label="Thư viện nội dung đề cử">
      <div className="relative grid min-h-[14rem] place-items-center overflow-hidden rounded-xl border border-white/10 bg-ink-900 @min-[40rem]/work:min-h-[28rem] @min-[40rem]/work:rounded-3xl">
        {selected.kind === "IMAGE" && selected.url ? (
          <Image
            alt={selected.altText || title}
            className="object-contain"
            fill
            priority
            sizes="100vw"
            src={selected.url}
            unoptimized
          />
        ) : null}
        {selected.kind === "VIDEO" && selected.url ? (
          <AdaptiveVideo
            autoPlay={selected.autoplay}
            className={`max-h-[42rem] w-full ${selected.fitMode === "COVER" ? "object-cover" : "object-contain"}`}
            controls={selected.controlsPreset !== "NONE"}
            controlsList={
              selected.controlsPreset === "MINIMAL"
                ? "nodownload noplaybackrate"
                : undefined
            }
            loop={selected.loop}
            muted={selected.muted}
            poster={selected.posterUrl ?? undefined}
            streamingUrl={selected.streamingUrl}
            fallbackUrl={selected.url}
          />
        ) : null}
        {selected.kind === "AUDIO" && selected.url ? (
          <audio
            className="w-[min(90%,40rem)]"
            controls
            preload="metadata"
            src={selected.url}
          />
        ) : null}
        {selected.kind === "DOCUMENT" && selected.url ? (
          <a
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/15 px-5 font-bold text-white"
            href={selected.url}
            rel="noreferrer"
            target="_blank"
          >
            <FileText className="size-5" /> Mở tài liệu công khai{" "}
            <ExternalLink className="size-4" />
          </a>
        ) : null}
        {!selected.url ? (
          <div className="text-center text-slate-500">
            <FileText className="mx-auto size-9" />
            <p className="mt-3 text-sm">
              Nội dung này chưa có bản xem trước công khai.
            </p>
          </div>
        ) : null}
      </div>
      {selected.caption ? (
        <p className="mt-3 text-center text-sm text-slate-500">
          {selected.caption}
        </p>
      ) : null}
      {media.length > 1 ? (
        <div className="mt-4 flex gap-3 overflow-x-auto pb-2">
          {media.map((item, index) => (
            <button
              aria-label={`Xem nội dung ${index + 1}`}
              aria-pressed={item.id === selected?.id}
              className={`min-h-12 shrink-0 rounded-xl border px-4 text-sm font-bold ${item.id === selected?.id ? "border-gold-300 text-gold-300" : "border-white/10 text-slate-400"}`}
              key={item.id}
              onClick={() => setSelectedId(item.id)}
              type="button"
            >
              {item.kind} {index + 1}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function CertificatePanel({
  certificate,
}: {
  certificate: PublicWorkDetail["certificate"];
}) {
  return (
    <section className="py-6">
      <FileCheck2 className="size-7 text-gold-300" />
      <h2 className="mt-4 font-bold text-white">Chứng nhận công khai</h2>
      {certificate ? (
        <>
          <dl className="mt-4 space-y-3 text-sm">
            <DataRow
              label="Số chứng thư"
              value={certificate.certificateNumber}
              mono
            />
            <DataRow label="Trạng thái chứng thư" value={certificate.status} />
            <DataRow
              label="Ngày phát hành"
              value={new Intl.DateTimeFormat("vi-VN").format(
                new Date(certificate.issuedAt),
              )}
            />
          </dl>
          <Link
            className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary-600 px-4 text-sm font-bold text-white"
            href={`/verify/${encodeURIComponent(certificate.certificateNumber)}`}
          >
            Xem và kiểm tra chứng thư <ExternalLink className="size-4" />
          </Link>
        </>
      ) : (
        <p className="mt-3 text-sm leading-6 text-slate-500">
          Chưa có chứng nhận được phép công bố.
        </p>
      )}
    </section>
  );
}

function ProofPanel({
  proof,
  verification,
  verificationPending,
}: {
  proof: PublicWorkDetail["proof"];
  verification?: Verification;
  verificationPending: boolean;
}) {
  const state = verificationState(proof, verification, verificationPending);
  return (
    <section className="py-6">
      <div className="flex items-start justify-between gap-3">
        <Blocks className="size-7 text-gold-300" />
        {state.icon}
      </div>
      <h2 className="mt-4 font-bold text-white">Thông tin minh bạch</h2>
      <p className={`mt-2 text-sm font-bold ${state.color}`}>{state.label}</p>
      <p className="mt-2 text-xs leading-5 text-slate-500">
        {state.description}
      </p>
      {proof ? (
        <dl className="mt-5 space-y-3 text-sm">
          <DataRow label="Nơi ghi nhận" value={proof.network} mono />
          <DataRow
            label="Mã đối chiếu"
            value={proof.transactionHash || "Đang cập nhật"}
            mono
          />
          <DataRow label="Xác nhận" value={String(proof.confirmations)} />
        </dl>
      ) : null}
      {verification?.explorerUrl ? (
        <a
          className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-gold-300"
          href={verification.explorerUrl}
          rel="noreferrer"
          target="_blank"
        >
          Xem bản ghi độc lập <ExternalLink className="size-4" />
        </a>
      ) : null}
    </section>
  );
}

function verificationState(
  proof: PublicWorkDetail["proof"],
  verification: Verification | undefined,
  pending: boolean,
) {
  if (!proof)
    return {
      label: "Chưa có thông tin đối chiếu",
      description:
        "Thông tin xác nhận độc lập chưa được công bố cho đề cử này.",
      color: "text-slate-400",
      icon: <CircleHelp className="size-5 text-slate-500" />,
    };
  if (pending)
    return {
      label: "Đang kiểm tra trạng thái",
      description: "Hệ thống đang đọc thông tin xác nhận mới nhất.",
      color: "text-amber-300",
      icon: <RotateCcw className="size-5 animate-spin text-amber-300" />,
    };
  if (!verification || verification.status === "PENDING")
    return {
      label: "Chưa thể đối chiếu lúc này",
      description:
        "Thông tin công khai vẫn được hiển thị, nhưng trạng thái xác nhận đang tạm thời gián đoạn.",
      color: "text-amber-300",
      icon: <AlertTriangle className="size-5 text-amber-300" />,
    };
  if (verification.status === "VALID")
    return {
      label: "Thông tin đã được đối chiếu",
      description: "Nội dung công khai khớp với bản ghi xác nhận độc lập.",
      color: "text-emerald-300",
      icon: <ShieldCheck className="size-5 text-emerald-300" />,
    };
  return {
    label: `Cần kiểm tra: ${verification.status}`,
    description:
      "Trạng thái hiện tại chưa đủ điều kiện xác nhận. Vui lòng kiểm tra lại trước khi sử dụng thông tin.",
    color: "text-red-300",
    icon: <AlertTriangle className="size-5 text-red-300" />,
  };
}

function DataRow({
  label,
  mono = false,
  value,
}: {
  label: string;
  mono?: boolean;
  value: string;
}) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd
        className={`mt-1 break-all text-white ${mono ? "font-mono text-xs" : "font-semibold"}`}
      >
        {value}
      </dd>
    </div>
  );
}

function UnavailableWork() {
  return (
    <div className="public-status-layout">
      <section
        aria-labelledby="unavailable-work-title"
        className="public-status-panel"
        role="status"
      >
        <AlertTriangle
          aria-hidden="true"
          className="public-status-panel__icon mx-auto size-9"
        />
        <h1
          className="public-status-panel__title mt-5 text-2xl font-bold"
          id="unavailable-work-title"
        >
          Tác phẩm không còn công khai
        </h1>
        <p className="public-status-panel__copy mt-2 text-sm leading-6">
          Nội dung có thể đã được ẩn hoặc tạm ngưng sau khi bạn mở trang.
        </p>
        <Link
          className="public-status-panel__action mt-6 inline-flex min-h-11 gap-2 px-5 text-sm font-bold"
          href="/works"
        >
          <ArrowLeft className="size-4" /> Trở lại danh sách đề cử
        </Link>
      </section>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div
      aria-label="Đang tải tác phẩm"
      className="mx-auto min-h-[70dvh] max-w-[90rem] animate-pulse px-4 py-16"
    >
      <div className="h-5 w-32 rounded bg-ink-800" />
      <div className="mt-6 h-16 max-w-3xl rounded bg-ink-800" />
      <div className="mt-12 aspect-[16/7] rounded-3xl bg-ink-900" />
    </div>
  );
}
