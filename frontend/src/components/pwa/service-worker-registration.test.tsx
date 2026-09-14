import { render, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  ServiceWorkerRegistration,
  shouldRegisterServiceWorker,
} from "@/components/pwa/service-worker-registration";

describe("ServiceWorkerRegistration", () => {
  it("only enables registration in a secure production environment", () => {
    expect(
      shouldRegisterServiceWorker({
        environment: "production",
        isSecureContext: true,
        supported: true,
      }),
    ).toBe(true);
    expect(
      shouldRegisterServiceWorker({
        environment: "development",
        isSecureContext: true,
        supported: true,
      }),
    ).toBe(false);
    expect(
      shouldRegisterServiceWorker({
        environment: "production",
        isSecureContext: false,
        supported: true,
      }),
    ).toBe(false);
  });

  it("registers the root-scoped service worker", async () => {
    const register = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(window, "isSecureContext", {
      configurable: true,
      value: true,
    });
    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: { register },
    });

    render(<ServiceWorkerRegistration environment="production" />);

    await waitFor(() =>
      expect(register).toHaveBeenCalledWith("/sw.js", { scope: "/" }),
    );
  });
});
