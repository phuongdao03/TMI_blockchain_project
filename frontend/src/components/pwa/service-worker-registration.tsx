"use client";

import { useEffect } from "react";

export function shouldRegisterServiceWorker({
  environment,
  isSecureContext,
  supported,
}: {
  environment: string;
  isSecureContext: boolean;
  supported: boolean;
}) {
  return environment === "production" && isSecureContext && supported;
}

export function ServiceWorkerRegistration({
  environment = process.env.NODE_ENV,
}: {
  environment?: string;
}) {
  useEffect(() => {
    if (
      !shouldRegisterServiceWorker({
        environment,
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
  }, [environment]);

  return null;
}
