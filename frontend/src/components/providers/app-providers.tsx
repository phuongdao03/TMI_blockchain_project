"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Suspense, type ReactNode, useState } from "react";

import { ServiceWorkerRegistration } from "@/components/pwa/service-worker-registration";
import { NavigationLoading } from "@/components/ui/navigation-loading";
import { ApiError } from "@/lib/api/client";

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: (failureCount, error) =>
              failureCount < 1 &&
              (!(error instanceof ApiError) || error.status >= 500),
            retryDelay: 400,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ServiceWorkerRegistration
        forceEnable={process.env.NEXT_PUBLIC_ENABLE_PWA === "true"}
      />
      <Suspense fallback={null}>
        <NavigationLoading />
      </Suspense>
      {children}
    </QueryClientProvider>
  );
}
