"use client";

import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { usePathname } from "next/navigation";

import { authApi } from "@/lib/api/client";

function SessionBootstrap() {
  const pathname = usePathname();
  const publicPath =
    pathname === "/" ||
    ["/works", "/search", "/map", "/verify"].some(
      (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
    );
  useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.currentUser,
    retry: false,
    staleTime: 60_000,
    enabled: !publicPath,
  });
  return null;
}

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
      <SessionBootstrap />
      {children}
    </QueryClientProvider>
  );
}
