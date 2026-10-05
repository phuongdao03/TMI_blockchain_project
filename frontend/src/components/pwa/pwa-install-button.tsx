"use client";

import { Download } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

type InstallChoice = { outcome: "accepted" | "dismissed"; platform: string };
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<InstallChoice>;
}
type NavigatorWithStandalone = Navigator & { standalone?: boolean };
const INSTALL_PROMPT_READY = "pwa-install-prompt-ready";

let deferredPrompt: BeforeInstallPromptEvent | null = null;

function isStandalone() {
  if (typeof window === "undefined") return false;
  return (
    (typeof window.matchMedia === "function" &&
      window.matchMedia("(display-mode: standalone)").matches) ||
    (navigator as NavigatorWithStandalone).standalone === true
  );
}

function isAppleMobile() {
  return (
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1)
  );
}

export function PwaInstallButton({ className }: { className?: string }) {
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    const standaloneCheck = window.setTimeout(() => {
      if (isStandalone()) setInstalled(true);
    }, 0);
    const capture = (event: Event) => {
      event.preventDefault();
      deferredPrompt = event as BeforeInstallPromptEvent;
      window.dispatchEvent(new Event(INSTALL_PROMPT_READY));
    };
    const markInstalled = () => setInstalled(true);
    window.addEventListener("beforeinstallprompt", capture);
    window.addEventListener("appinstalled", markInstalled);
    return () => {
      window.clearTimeout(standaloneCheck);
      window.removeEventListener("beforeinstallprompt", capture);
      window.removeEventListener("appinstalled", markInstalled);
    };
  }, []);

  if (installed) return null;
  return (
    <Link
      aria-label="Xem hướng dẫn cài ứng dụng"
      className={cn(
        "group inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-full border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm font-bold text-[var(--theme-text)] transition hover:border-primary-500 hover:bg-[var(--theme-surface-soft)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-700 sm:px-4",
        className,
      )}
      href="/install"
    >
      <Download
        aria-hidden="true"
        className="size-4 transition-transform group-hover:translate-y-0.5"
      />
      <span className="hidden whitespace-nowrap lg:inline">Cài ứng dụng</span>
    </Link>
  );
}

export function PwaInstallAction() {
  const [state, setState] = useState<
    "idle" | "working" | "accepted" | "installed"
  >("idle");
  const [platform, setPlatform] = useState<"unknown" | "ios" | "other">(
    "unknown",
  );
  const [promptReady, setPromptReady] = useState(false);

  useEffect(() => {
    const refresh = () => setPromptReady(Boolean(deferredPrompt));
    const detect = window.setTimeout(() => {
      setPlatform(isAppleMobile() ? "ios" : "other");
      refresh();
      if (isStandalone()) setState("installed");
    }, 0);
    const installed = () => setState("installed");
    window.addEventListener(INSTALL_PROMPT_READY, refresh);
    window.addEventListener("appinstalled", installed);
    return () => {
      window.clearTimeout(detect);
      window.removeEventListener(INSTALL_PROMPT_READY, refresh);
      window.removeEventListener("appinstalled", installed);
    };
  }, []);

  async function install() {
    if (!deferredPrompt) {
      setPromptReady(false);
      return;
    }
    setState("working");
    try {
      await deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      deferredPrompt = null;
      setPromptReady(false);
      setState(choice.outcome === "accepted" ? "accepted" : "idle");
    } catch {
      deferredPrompt = null;
      setPromptReady(false);
      setState("idle");
    }
  }

  if (state === "installed") {
    return (
      <p className="text-sm font-bold text-emerald-400" role="status">
        Ứng dụng đã được cài đặt.
      </p>
    );
  }
  if (state === "accepted") {
    return (
      <p className="text-sm font-semibold text-emerald-400" role="status">
        Đã xác nhận cài đặt. Kiểm tra biểu tượng ứng dụng trên thiết bị.
      </p>
    );
  }
  if (platform === "unknown") {
    return (
      <p className="text-sm text-[var(--theme-muted)]">
        Đang kiểm tra trình duyệt…
      </p>
    );
  }
  if (platform === "ios") {
    return (
      <div className="space-y-4">
        <p className="text-sm leading-6 text-[var(--theme-muted)]">
          Trên iPhone hoặc iPad, mở trang bằng Safari rồi chạm Chia sẻ → Thêm
          vào Màn hình chính → Thêm. Safari cần bạn xác nhận bước này.
        </p>
        <a className="install-guide__manual-link" href="#install-device-steps">
          Xem các bước trên iPhone
        </a>
      </div>
    );
  }
  if (!promptReady) {
    return (
      <div className="space-y-4">
        <p className="text-sm leading-6 text-[var(--theme-muted)]">
          Trình duyệt chưa cung cấp hộp thoại cài đặt. Bạn có thể cài từ menu
          trình duyệt theo hướng dẫn bên cạnh.
        </p>
        <a className="install-guide__manual-link" href="#install-device-steps">
          Xem cách cài trên thiết bị
        </a>
      </div>
    );
  }
  return (
    <div>
      <button
        className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-full bg-primary-700 px-6 text-sm font-bold text-white transition hover:bg-primary-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 sm:w-auto"
        disabled={state === "working"}
        onClick={() => void install()}
        type="button"
      >
        <Download aria-hidden="true" className="size-5" />
        {state === "working" ? "Đang mở cài đặt…" : "Tiến hành cài đặt"}
      </button>
    </div>
  );
}
