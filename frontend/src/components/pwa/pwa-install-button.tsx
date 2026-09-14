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

let deferredPrompt: BeforeInstallPromptEvent | null = null;

function isStandalone() {
  if (typeof window === "undefined") return false;
  return (
    (typeof window.matchMedia === "function" &&
      window.matchMedia("(display-mode: standalone)").matches) ||
    (navigator as NavigatorWithStandalone).standalone === true
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
      <Download aria-hidden="true" className="size-4 transition-transform group-hover:translate-y-0.5" />
      <span className="hidden whitespace-nowrap lg:inline">Cài ứng dụng</span>
    </Link>
  );
}

export function PwaInstallAction() {
  const [state, setState] = useState<"idle" | "working" | "installed" | "manual">("idle");

  async function install() {
    if (!deferredPrompt) return setState("manual");
    setState("working");
    try {
      await deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      deferredPrompt = null;
      setState(choice.outcome === "accepted" ? "installed" : "idle");
    } catch {
      deferredPrompt = null;
      setState("manual");
    }
  }

  if (state === "installed") {
    return <p className="text-sm font-bold text-emerald-400" role="status">Ứng dụng đã được cài đặt.</p>;
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
      {state === "manual" ? (
        <p className="mt-3 max-w-xl text-sm leading-6 text-slate-400" role="status">
          Trình duyệt chưa mở hộp thoại tự động. Hãy dùng menu trình duyệt và chọn <strong>Cài đặt ứng dụng</strong> hoặc <strong>Thêm vào màn hình chính</strong>.
        </p>
      ) : null}
    </div>
  );
}
