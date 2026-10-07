"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Suspense, type ReactNode, useState } from "react";

import { ServiceWorkerRegistration } from "@/components/pwa/service-worker-registration";
import { NavigationLoading } from "@/components/ui/navigation-loading";

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
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
