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

function storedInstallPrompt(): BeforeInstallPromptEvent | null {
  return (
    (window as Window & { __thvInstallPrompt?: BeforeInstallPromptEvent })
      .__thvInstallPrompt ?? null
  );
}

function clearInstallPrompt() {
  delete (window as Window & { __thvInstallPrompt?: BeforeInstallPromptEvent })
    .__thvInstallPrompt;
}

function captureInstallPrompt(event: Event) {
  event.preventDefault();
  (
    window as Window & { __thvInstallPrompt?: BeforeInstallPromptEvent }
  ).__thvInstallPrompt = event as BeforeInstallPromptEvent;
  window.dispatchEvent(new Event(INSTALL_PROMPT_READY));
}

async function requestInstall() {
  const prompt = storedInstallPrompt();
  if (!prompt) return null;
  clearInstallPrompt();
  window.dispatchEvent(new Event(INSTALL_PROMPT_READY));
  await prompt.prompt();
  return (await prompt.userChoice).outcome;
}

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
  const [promptReady, setPromptReady] = useState(false);
  const [working, setWorking] = useState(false);
  const [appleMobile, setAppleMobile] = useState(false);

  useEffect(() => {
    const standaloneCheck = window.setTimeout(() => {
      if (isStandalone()) setInstalled(true);
      setAppleMobile(isAppleMobile());
    }, 0);
    const refresh = () => setPromptReady(Boolean(storedInstallPrompt()));
    const markInstalled = () => {
      clearInstallPrompt();
      setPromptReady(false);
      setInstalled(true);
    };
    refresh();
    window.addEventListener("beforeinstallprompt", captureInstallPrompt);
    window.addEventListener(INSTALL_PROMPT_READY, refresh);
    window.addEventListener("appinstalled", markInstalled);
    return () => {
      window.clearTimeout(standaloneCheck);
      window.removeEventListener("beforeinstallprompt", captureInstallPrompt);
      window.removeEventListener(INSTALL_PROMPT_READY, refresh);
      window.removeEventListener("appinstalled", markInstalled);
    };
  }, []);

  if (installed) return null;
  const actionLabel = appleMobile
    ? "Thêm vào Màn hình chính"
    : promptReady
      ? "Cài ứng dụng"
      : "Cách cài ứng dụng";
  const actionClass = cn(
    "pwa-install-button group inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-full border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm font-bold text-[var(--theme-text)] transition hover:border-primary-500 hover:bg-[var(--theme-surface-soft)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-700 sm:px-4",
    className,
  );
  const content = (
    <>
      <Download
        aria-hidden="true"
        className="size-4 transition-transform group-hover:translate-y-0.5 motion-reduce:transition-none"
      />
      <span className="pwa-install-button__label hidden whitespace-nowrap lg:inline">
        {working ? "Đang mở cài đặt…" : actionLabel}
      </span>
    </>
  );
  if (promptReady && !appleMobile) {
    return (
      <button
        aria-label={actionLabel}
        className={actionClass}
        disabled={working}
        onClick={async () => {
          setWorking(true);
          try {
            const outcome = await requestInstall();
            if (outcome === "accepted") setInstalled(true);
          } catch {
            setPromptReady(false);
          } finally {
            setWorking(false);
          }
        }}
        type="button"
      >
        {content}
      </button>
    );
  }
  return (
    <Link aria-label={actionLabel} className={actionClass} href="/install">
      {content}
    </Link>
  );
}

export function PwaInstallAction() {
  const [state, setState] = useState<
    "idle" | "working" | "accepted" | "installed"
  >("idle");
  const [platform, setPlatform] = useState<
    "unknown" | "ios" | "android" | "desktop"
  >("unknown");
  const [promptReady, setPromptReady] = useState(false);
  const [manualNeeded, setManualNeeded] = useState(false);

  useEffect(() => {
    const refresh = () => {
      const ready = Boolean(storedInstallPrompt());
      setPromptReady(ready);
      if (ready) setManualNeeded(false);
    };
    const detect = window.setTimeout(() => {
      setPlatform(
        isAppleMobile()
          ? "ios"
          : /Android/i.test(navigator.userAgent)
            ? "android"
            : "desktop",
      );
      refresh();
      if (isStandalone()) setState("installed");
    }, 0);
    const installed = () => {
      clearInstallPrompt();
      setPromptReady(false);
      setState("installed");
    };
    window.addEventListener("beforeinstallprompt", captureInstallPrompt);
    window.addEventListener(INSTALL_PROMPT_READY, refresh);
    window.addEventListener("appinstalled", installed);
    return () => {
      window.clearTimeout(detect);
      window.removeEventListener("beforeinstallprompt", captureInstallPrompt);
      window.removeEventListener(INSTALL_PROMPT_READY, refresh);
      window.removeEventListener("appinstalled", installed);
    };
  }, []);

  async function install() {
    if (!storedInstallPrompt()) {
      setPromptReady(false);
      setManualNeeded(true);
      return;
    }
    setState("working");
    try {
      const outcome = await requestInstall();
      setPromptReady(false);
      setState(outcome === "accepted" ? "accepted" : "idle");
    } catch {
      clearInstallPrompt();
      setPromptReady(false);
      setManualNeeded(true);
      setState("idle");
    }
  }

  if (state === "installed") {
    return (
      <p
        className="text-sm font-bold text-emerald-700 dark:text-emerald-300"
        role="status"
      >
        Ứng dụng đã được cài đặt.
      </p>
    );
  }
  if (state === "accepted") {
    return (
      <p
        className="text-sm font-semibold text-emerald-700 dark:text-emerald-300"
        role="status"
      >
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
      <div className="space-y-3">
        <p
          className="text-sm leading-6 text-[var(--theme-muted)]"
          role="status"
        >
          {manualNeeded
            ? "Trình duyệt chưa mở được cửa sổ cài đặt. Bạn vẫn có thể cài từ menu trình duyệt."
            : platform === "android"
              ? "Chrome trên Android chưa hiển thị lời mời cài đặt. Mở menu ⋮ rồi chọn Cài đặt ứng dụng hoặc Thêm vào Màn hình chính."
              : "Chrome hoặc Edge trên máy tính chưa hiển thị lời mời cài đặt. Mở menu trình duyệt rồi chọn Cài đặt ứng dụng."}
        </p>
        <a className="install-guide__manual-link" href="#install-device-steps">
          {platform === "android"
            ? "Xem các bước trên Android"
            : "Xem các bước trên máy tính"}
        </a>
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <button
        className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-full bg-primary-700 px-6 text-sm font-bold text-white transition hover:bg-primary-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 sm:w-auto"
        disabled={state === "working"}
        onClick={() => void install()}
        type="button"
      >
        <Download aria-hidden="true" className="size-5" />
        {state === "working" ? "Đang mở cài đặt…" : "Cài ứng dụng"}
      </button>
      <p
        className="text-sm leading-6 text-[var(--theme-muted)]"
        role={manualNeeded ? "status" : undefined}
      >
        Nhấn nút để mở cửa sổ cài đặt của trình duyệt trên thiết bị này.
      </p>
      <a className="install-guide__manual-link" href="#install-device-steps">
        {platform === "android"
          ? "Xem các bước trên Android"
          : "Xem các bước trên máy tính"}
      </a>
    </div>
  );
}
