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
  ImageOff,
  RotateCcw,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

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
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  });
  const error = detail.error as ApiError | null;

  if (detail.isPending) return <DetailSkeleton />;
  if (error?.status === 404) return <UnavailableWork />;
  if (detail.error || !detail.data) {
    return (
      <div className="mx-auto grid min-h-[60dvh] max-w-xl place-items-center px-4 text-center">
        <div>
          <CircleHelp className="mx-auto size-9 text-gold-300" />
          <h1 className="mt-5 text-2xl font-bold text-white">Chưa thể tải tác phẩm</h1>
          <p className="mt-2 text-sm leading-6 text-slate-400">Dịch vụ công khai đang gián đoạn. Hãy thử lại sau ít phút.</p>
          <Button className="mt-5" onClick={() => detail.refetch()}><RotateCcw className="size-4" /> Thử lại</Button>
        </div>
      </div>
    );
  }
  return <PublicWorkPresentation detail={detail.data} />;
}

function PublicWorkPresentation({ detail }: { detail: PublicWorkDetail }) {
  useEffect(() => {
    void publicApi.recordView(detail.canonicalSlug).catch(() => undefined);
  }, [detail.canonicalSlug]);

  const verification = useQuery({
    queryKey: ["public-work-verification", detail.certificate?.certificateNumber],
    queryFn: () => publicApi.verifyNumber(detail.certificate!.certificateNumber),
    enabled: Boolean(detail.certificate?.certificateNumber),
    retry: false,
    staleTime: 60_000,
  });
  return (
    <article className="relative isolate overflow-hidden">
      <header className="border-b border-white/10 px-4 py-10 sm:px-6 lg:py-16">
        <div className="mx-auto max-w-[90rem]">
          <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm text-slate-500">
            <Link className="inline-flex items-center gap-1 hover:text-white" href="/thu-vien"><ArrowLeft className="size-4" /> Catalog</Link>
            <span aria-hidden="true">/</span><span>{detail.categoryName}</span>
          </nav>
          <div className="mt-9 grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-end">
            <div>
              <p className="text-xs font-bold tracking-[0.2em] text-gold-300 uppercase">{detail.categoryName}</p>
              <h1 className="mt-4 max-w-5xl text-4xl font-bold tracking-[-0.045em] text-white sm:text-6xl lg:text-7xl">{detail.title}</h1>
              <p className="mt-6 max-w-3xl text-base leading-8 text-slate-300 sm:text-lg">{detail.shortDescription}</p>
            </div>
            <dl className="grid gap-4 border-l border-white/10 pl-5 text-sm">
              <div><dt className="text-xs tracking-wide text-slate-500 uppercase">Tác giả công khai</dt><dd className="mt-1 flex items-center gap-2 font-bold text-white"><UserRound className="size-4 text-gold-300" />{detail.authorDisplayName || "Chưa công bố"}</dd></div>
              {detail.organizationDisplayName ? <div><dt className="text-xs tracking-wide text-slate-500 uppercase">Tổ chức</dt><dd className="mt-1 font-bold text-white">{detail.organizationDisplayName}</dd></div> : null}
              <div><dt className="text-xs tracking-wide text-slate-500 uppercase">Ngày công bố</dt><dd className="mt-1 flex items-center gap-2 text-white"><CalendarDays className="size-4 text-gold-300" /><time dateTime={detail.publishedAt}>{new Intl.DateTimeFormat("vi-VN", { dateStyle: "long" }).format(new Date(detail.publishedAt))}</time></dd></div>
            </dl>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[90rem] px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
        <PublicGallery media={detail.media} title={detail.title} />
        <div className="mt-12 grid gap-8 lg:grid-cols-[minmax(0,1fr)_24rem]">
          <div className="min-w-0">
            <section aria-labelledby="about-work-heading" className="border-t border-white/10 pt-7">
              <p className="text-xs font-bold tracking-[0.2em] text-primary-400 uppercase">Public narrative</p>
              <h2 className="mt-2 text-3xl font-bold text-white" id="about-work-heading">Về tác phẩm</h2>
              {detail.fullDescription ? <p className="mt-6 max-w-4xl whitespace-pre-wrap break-words text-base leading-8 text-slate-300">{detail.fullDescription}</p> : <p className="mt-5 text-sm text-slate-500">Tác phẩm chưa có phần giới thiệu mở rộng.</p>}
              <div className="mt-8 flex flex-wrap gap-2">{detail.tags.map((tag) => <Link className="rounded-full border border-white/10 px-3 py-1.5 text-xs font-bold text-slate-300 hover:border-gold-300" href={`/thu-vien?tag=${encodeURIComponent(tag.slug)}`} key={tag.slug}>#{tag.name}</Link>)}</div>
            </section>
            <PublicWorkShareControls detail={detail} />
          </div>
          <aside className="space-y-4">
            <CertificatePanel certificate={detail.certificate} />
            <ProofPanel proof={detail.proof} verification={verification.data} verificationPending={verification.isPending && verification.fetchStatus === "fetching"} />
          </aside>
        </div>

        {detail.relatedWorks.length ? (
          <section aria-labelledby="related-heading" className="mt-16 border-t border-white/10 pt-10">
            <p className="text-xs font-bold tracking-[0.2em] text-gold-300 uppercase">Khám phá tiếp</p>
            <h2 className="mt-2 text-3xl font-bold text-white" id="related-heading">Tác phẩm liên quan</h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{detail.relatedWorks.map((work, index) => <PublicWorkCard key={work.id} position={index + 1} source="list" work={work} />)}</div>
          </section>
        ) : null}
      </div>
    </article>
  );
}

function PublicGallery({ media, title }: { media: PublicWorkDetailMedia[]; title: string }) {
  const [selectedId, setSelectedId] = useState(media.find((item) => item.isThumbnail)?.id ?? media[0]?.id);
  const selected = media.find((item) => item.id === selectedId) ?? media[0];
  if (!selected) return <div className="grid aspect-[16/8] place-items-center rounded-3xl border border-dashed border-white/15 bg-ink-900"><div className="text-center"><ImageOff className="mx-auto size-9 text-slate-600" /><p className="mt-3 text-sm text-slate-500">Chưa có media công khai</p></div></div>;
  return (
    <section aria-label="Thư viện media tác phẩm">
      <div className="relative grid min-h-[22rem] place-items-center overflow-hidden rounded-3xl border border-white/10 bg-ink-900 sm:min-h-[34rem]">
        {selected.kind === "IMAGE" && selected.url ? <Image alt={selected.altText || title} className="object-contain" fill priority sizes="100vw" src={selected.url} unoptimized /> : null}
        {selected.kind === "VIDEO" && selected.url ? <video className="max-h-[42rem] w-full" controls src={selected.url}><track kind="captions" /></video> : null}
        {selected.kind === "AUDIO" && selected.url ? <audio className="w-[min(90%,40rem)]" controls src={selected.url} /> : null}
        {selected.kind === "DOCUMENT" && selected.url ? <a className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/15 px-5 font-bold text-white" href={selected.url} rel="noreferrer" target="_blank"><FileText className="size-5" /> Mở tài liệu công khai <ExternalLink className="size-4" /></a> : null}
        {!selected.url ? <div className="text-center text-slate-500"><FileText className="mx-auto size-9" /><p className="mt-3 text-sm">Media này không có bản xem trước công khai.</p></div> : null}
      </div>
      {selected.caption ? <p className="mt-3 text-center text-sm text-slate-500">{selected.caption}</p> : null}
      {media.length > 1 ? <div className="mt-4 flex gap-3 overflow-x-auto pb-2">{media.map((item, index) => <button aria-label={`Xem media ${index + 1}`} aria-pressed={item.id === selected?.id} className={`min-h-12 shrink-0 rounded-xl border px-4 text-sm font-bold ${item.id === selected?.id ? "border-gold-300 text-gold-300" : "border-white/10 text-slate-400"}`} key={item.id} onClick={() => setSelectedId(item.id)} type="button">{item.kind} {index + 1}</button>)}</div> : null}
    </section>
  );
}

function CertificatePanel({ certificate }: { certificate: PublicWorkDetail["certificate"] }) {
  return <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"><FileCheck2 className="size-7 text-gold-300" /><h2 className="mt-4 font-bold text-white">Chứng nhận công khai</h2>{certificate ? <dl className="mt-4 space-y-3 text-sm"><DataRow label="Số chứng nhận" value={certificate.certificateNumber} mono /><DataRow label="Trạng thái DB" value={certificate.status} /><DataRow label="Ngày phát hành" value={new Intl.DateTimeFormat("vi-VN").format(new Date(certificate.issuedAt))} /></dl> : <p className="mt-3 text-sm leading-6 text-slate-500">Chưa có chứng nhận được phép công bố.</p>}</section>;
}

function ProofPanel({ proof, verification, verificationPending }: { proof: PublicWorkDetail["proof"]; verification?: Verification; verificationPending: boolean }) {
  const state = verificationState(proof, verification, verificationPending);
  return <section className="rounded-2xl border border-white/10 bg-ink-900 p-5"><div className="flex items-start justify-between gap-3"><Blocks className="size-7 text-gold-300" />{state.icon}</div><h2 className="mt-4 font-bold text-white">Bằng chứng blockchain</h2><p className={`mt-2 text-sm font-bold ${state.color}`}>{state.label}</p><p className="mt-2 text-xs leading-5 text-slate-500">{state.description}</p>{proof ? <dl className="mt-5 space-y-3 text-sm"><DataRow label="Mạng" value={proof.network} mono /><DataRow label="Transaction" value={proof.transactionHash || "Chưa broadcast"} mono /><DataRow label="Xác nhận" value={String(proof.confirmations)} /></dl> : null}{verification?.explorerUrl ? <a className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-gold-300" href={verification.explorerUrl} rel="noreferrer" target="_blank">Mở blockchain explorer <ExternalLink className="size-4" /></a> : null}</section>;
}

function verificationState(proof: PublicWorkDetail["proof"], verification: Verification | undefined, pending: boolean) {
  if (!proof) return { label: "Chưa có bản ghi giao dịch", description: "Hệ thống chưa lưu bằng chứng blockchain cho projection này.", color: "text-slate-400", icon: <CircleHelp className="size-5 text-slate-500" /> };
  if (pending) return { label: "Đang đối chiếu RPC", description: "Đang đọc trạng thái mới nhất từ mạng blockchain.", color: "text-amber-300", icon: <RotateCcw className="size-5 animate-spin text-amber-300" /> };
  if (!verification || verification.status === "PENDING") return { label: "RPC tạm thời chưa khả dụng", description: "Bản ghi DB vẫn được hiển thị nhưng chưa thể xác nhận on-chain lúc này.", color: "text-amber-300", icon: <AlertTriangle className="size-5 text-amber-300" /> };
  if (verification.status === "VALID") return { label: "Đã đối chiếu on-chain", description: "Hash và phiên bản công khai khớp dữ liệu trên blockchain.", color: "text-emerald-300", icon: <ShieldCheck className="size-5 text-emerald-300" /> };
  return { label: `Cần kiểm tra: ${verification.status}`, description: "Trạng thái xác minh không đạt điều kiện VALID. Không nên coi đây là bằng chứng đã xác nhận.", color: "text-red-300", icon: <AlertTriangle className="size-5 text-red-300" /> };
}

function DataRow({ label, mono = false, value }: { label: string; mono?: boolean; value: string }) { return <div><dt className="text-xs text-slate-500">{label}</dt><dd className={`mt-1 break-all text-white ${mono ? "font-mono text-xs" : "font-semibold"}`}>{value}</dd></div>; }

function UnavailableWork() { return <div className="mx-auto grid min-h-[60dvh] max-w-xl place-items-center px-4 text-center"><div><AlertTriangle className="mx-auto size-9 text-amber-300" /><h1 className="mt-5 text-2xl font-bold text-white">Tác phẩm không còn công khai</h1><p className="mt-2 text-sm leading-6 text-slate-400">Nội dung có thể đã được ẩn hoặc tạm ngưng sau khi bạn mở trang.</p><Link className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/15 px-4 text-sm font-bold text-white" href="/thu-vien"><ArrowLeft className="size-4" /> Trở lại catalog</Link></div></div>; }

function DetailSkeleton() { return <div aria-label="Đang tải tác phẩm" className="mx-auto min-h-[70dvh] max-w-[90rem] animate-pulse px-4 py-16"><div className="h-5 w-32 rounded bg-ink-800" /><div className="mt-6 h-16 max-w-3xl rounded bg-ink-800" /><div className="mt-12 aspect-[16/7] rounded-3xl bg-ink-900" /></div>; }
