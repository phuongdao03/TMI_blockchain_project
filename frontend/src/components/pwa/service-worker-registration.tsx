"use client";

import { useEffect } from "react";

export function shouldRegisterServiceWorker({
  environment,
  forceEnable = false,
  isSecureContext,
  supported,
}: {
  environment: string;
  forceEnable?: boolean;
  isSecureContext: boolean;
  supported: boolean;
}) {
  return (
    (environment === "production" || forceEnable) &&
    isSecureContext &&
    supported
  );
}

export function ServiceWorkerRegistration({
  environment = process.env.NODE_ENV,
  forceEnable = false,
}: {
  environment?: string;
  forceEnable?: boolean;
}) {
  useEffect(() => {
    if (
      !shouldRegisterServiceWorker({
        environment,
        forceEnable,
        isSecureContext: window.isSecureContext,
        supported: "serviceWorker" in navigator,
      })
    ) {
      return;
    }

    const register = () => {
      void navigator.serviceWorker
        .register("/sw.js", { scope: "/" })
        .catch(() => undefined);
    };

    if (document.readyState === "complete") {
      register();
      return;
    }

    window.addEventListener("load", register, { once: true });
    return () => window.removeEventListener("load", register);
  }, [environment, forceEnable]);

  return null;
}
